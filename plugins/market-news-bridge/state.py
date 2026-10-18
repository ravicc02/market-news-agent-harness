
"""Small durable inbox for RSS-to-Agent delivery. No credentials are stored."""
import json,sqlite3,time,uuid
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from hashlib import sha256


def identity(url):
    p=urlsplit(url)
    query=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,urlencode(query),''))


class Inbox:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS feeds(url TEXT PRIMARY KEY,baseline_at REAL,last_check REAL,last_error TEXT);
        CREATE TABLE IF NOT EXISTS seen(k TEXT PRIMARY KEY,url TEXT,first_seen REAL,reason TEXT);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,k TEXT UNIQUE,payload TEXT,status TEXT,attempts INTEGER DEFAULT 0,next_try REAL DEFAULT 0,created REAL,updated REAL,report_path TEXT,error TEXT);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,event TEXT,created REAL,detail TEXT);
        ''')
        self.db.execute("UPDATE jobs SET status='QUEUED',error='Restarted before delivery',updated=? WHERE status='RUNNING'",(time.time(),))
        self.db.execute("UPDATE jobs SET status='UNKNOWN',error='Restart during delivery; do not auto-retry',updated=? WHERE status='SENDING'",(time.time(),))

    def event(self,job,event,detail=None):
        self.db.execute('INSERT INTO events(job_id,event,created,detail) VALUES (?,?,?,?)',(job,event,time.time(),json.dumps(detail or {},ensure_ascii=False)))

    def ingest(self,url,session,rows,*,force_test=False):
        key=lambda row:sha256((session+'|'+identity(row['url'])).encode()).hexdigest()
        baseline=self.db.execute('SELECT baseline_at FROM feeds WHERE url=?',(url,)).fetchone()
        added=[];now=time.time()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('INSERT INTO feeds(url,baseline_at,last_check) VALUES (?,?,?) ON CONFLICT(url) DO UPDATE SET last_check=excluded.last_check,last_error=NULL',(url,now,now))
            for row in rows:
                k=key(row)
                if force_test:k='test:'+uuid.uuid4().hex
                if not force_test and self.db.execute('SELECT 1 FROM seen WHERE k=?',(k,)).fetchone():continue
                reason='BASELINE' if (baseline is None or baseline['baseline_at'] is None) and not force_test else 'IRRELEVANT' if not row.get('categories') else 'NEW'
                if reason=='NEW' and not force_test:
                    stamp=row.get('published_timestamp')
                    if not stamp or stamp>now+300 or stamp<now-86400:reason='OUTSIDE_WINDOW'
                self.db.execute('INSERT OR IGNORE INTO seen(k,url,first_seen,reason) VALUES (?,?,?,?)',(k,row['url'],now,reason))
                if reason!='NEW':continue
                job_id='news-'+sha256(k.encode()).hexdigest()[:16]
                payload={**row,'session':session,'test_mode':force_test,'job_id':job_id}
                self.db.execute("INSERT OR IGNORE INTO jobs(id,k,payload,status,created,updated) VALUES (?,?,?,'QUEUED',?,?)",(job_id,k,json.dumps(payload,ensure_ascii=False),now,now))
                self.event(job_id,'QUEUED',{'url':row['url'],'test_mode':force_test})
                added.append(job_id)
            self.db.commit()
        except BaseException:
            self.db.rollback();raise
        return added

    def next_job(self):
        row=self.db.execute("SELECT * FROM jobs WHERE status IN ('QUEUED','RENDERED','BLOCKED_CONTEXT') AND next_try<=? ORDER BY created LIMIT 1",(time.time(),)).fetchone()
        if row is None:return None
        value=dict(row);value['payload']=json.loads(value['payload']);return value

    def update(self,job,status,*,error=None,report_path=None,next_try=0,claim=False):
        self.db.execute('UPDATE jobs SET status=?,error=?,report_path=COALESCE(?,report_path),next_try=?,updated=?,attempts=attempts+? WHERE id=?',(status,error,report_path,next_try,time.time(),1 if claim else 0,job))
        self.event(job,status,{'error':error,'report_path':report_path})

    def summary(self):
        return {'jobs':{r[0]:r[1] for r in self.db.execute('SELECT status,COUNT(*) FROM jobs GROUP BY status')},'feeds':[dict(r) for r in self.db.execute('SELECT * FROM feeds ORDER BY url')],'recent':[dict(r) for r in self.db.execute('SELECT id,status,attempts,report_path,error,updated FROM jobs ORDER BY created DESC LIMIT 8')], 'seen_urls':self.db.execute('SELECT COUNT(*) FROM seen').fetchone()[0]}
