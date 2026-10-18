"""RSS -> original article -> native AstrBot Agent -> one durable proactive delivery."""
import asyncio,importlib.util,json,time
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from astrbot.api import AstrBotConfig,logger
from astrbot.api.star import Context,Star,register
from astrbot.api.event import filter,AstrMessageEvent,MessageChain
import astrbot.api.message_components as Comp
from .state import Inbox
from .agent import run_editor


@register('astrbot_plugin_market_news','Local','Financial news RSS-to-Agent bridge','0.1.0')
class MarketNews(Star):
    def __init__(self,context:Context,config:AstrBotConfig):
        super().__init__(context)
        self.context=context;self.config=config
        self.workspace=Path(config['workspace']).resolve()
        self.target=str(config['target_session'])
        self.data_dir=Path('/AstrBot/data/plugin_data/astrbot_plugin_market_news')
        self.data_dir.mkdir(parents=True,exist_ok=True)
        self.poll_log=self.workspace/'runs/poll-log.jsonl'
        self.poll_log.parent.mkdir(parents=True,exist_ok=True)
        self.inbox=Inbox(self.data_dir/'state.sqlite3')
        spec=importlib.util.spec_from_file_location('market_news_collector',self.workspace/'tools/fetch-news.py')
        self.collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.collector)
        self.sources=self.collector.settings()
        self.wake=asyncio.Event();self.tasks=[];self.source_errors={};self.running=None

    async def initialize(self):
        if not self.config.get('enabled',True):return
        self.context._market_news_handler=self
        # AstrBot initializes each plugin while scanning; dependencies may load later.
        self.tasks=[asyncio.create_task(self._start_when_ready())]

    async def _start_when_ready(self):
        for _ in range(120):
            rss=self._rss()
            platform=self.context.get_platform_inst(self.target.split(':',1)[0])
            if rss is not None and platform is not None:break
            await asyncio.sleep(0.5)
        else:
            self.source_errors['startup']='Waiting for RSS plugin and target WeChat adapter'
            self.status();return
        paused_urls={source['url'] for source in self.sources.get('paused_feeds',[])}
        for url, record in list(rss.data_handler.data.items()):
            if not isinstance(record,dict) or 'subscribers' not in record:continue
            if self.target in record['subscribers'] and url in paused_urls:
                record['subscribers'].pop(self.target,None)
                if not record['subscribers']:rss.data_handler.data.pop(url,None)
        for source in self.sources['feeds']:
            record=rss.data_handler.data.setdefault(source['url'],{'info':{'title':source['name'],'description':'Financial source managed by Market News bridge'},'subscribers':{}})
            record['subscribers'][self.target]={'cron_expr':self.config.get('poll_cron','*/2 * * * *'),'last_update':int(time.time()),'latest_link':''}
        rss.data_handler.save_data()
        rss._fresh_asyncIOScheduler()
        await self._bootstrap()
        self.tasks.extend([asyncio.create_task(self._worker()),asyncio.create_task(self._control_loop())])
        self.status()
        logger.info('Market News bridge ready: RSS monitoring + native Agent + proactive delivery')

    async def terminate(self):
        if getattr(self.context,'_market_news_handler',None) is self:delattr(self.context,'_market_news_handler')
        for task in self.tasks:task.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)
        self.inbox.db.close()

    def status(self):
        value={'updated_at':datetime.now(timezone.utc).isoformat(),'enabled':bool(self.config.get('enabled')),'running_job':self.running,'poll_cron':self.config.get('poll_cron'),'source_errors':self.source_errors,**self.inbox.summary()}
        active_urls={source['url'] for source in self.sources['feeds']}
        value['feeds']=[record for record in value['feeds'] if record['url'] in active_urls]
        value['configured_feeds']=len(self.sources['feeds'])
        value['paused_feeds']=[{'id':source['id'],'reason':source.get('reason')} for source in self.sources.get('paused_feeds',[])]
        target=self.workspace/'runs/monitor-status.json';target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temporary.replace(target)
        return value

    def _rss(self):
        return next((star.star_cls for star in self.context.get_all_stars() if star.name=='astrbot_plugin_rss' and star.activated and star.star_cls),None)

    def _rows(self,source,items):
        rows=[]
        for item in items:
            title=str(item.title or '');description=str(item.description or '')
            kinds=self.collector.categories(title+' '+description,self.sources)
            if not kinds:kinds=list(source.get('default_categories',['外汇货币对直盘'] if source['id'] in ('fed','ecb') else []))
            try:url=self.collector.checked_url(item.link,source['domains'])
            except ValueError:continue
            rows.append({'source_id':source['id'],'source':source['name'],'title':title,'url':url,'published_original':item.pubDate,'published_timestamp':item.pubDate_timestamp,'published_at':datetime.fromtimestamp(item.pubDate_timestamp,timezone.utc).isoformat() if item.pubDate_timestamp else None,'categories':kinds,'feed_summary_html':description})
        return rows

    async def _bootstrap(self):
        async def one(source):
            if self.inbox.db.execute('SELECT 1 FROM feeds WHERE url=? AND baseline_at IS NOT NULL',(source['url'],)).fetchone():return
            try:
                _,_,_,rows=await asyncio.to_thread(self.collector.discover,source,self.sources)
                for row in rows:row['published_timestamp']=self.collector.parse_time(row['published_original']).timestamp() if self.collector.parse_time(row['published_original']) else 0
                self.inbox.ingest(source['url'],self.target,rows)
                self.source_errors.pop(source['id'],None)
            except Exception as exc:self.source_errors[source['id']]=type(exc).__name__+': '+str(exc)[:160]
        await asyncio.gather(*(one(source) for source in self.sources['feeds']))

    async def ingest(self,url,session,items):
        if not self.config.get('enabled') or session!=self.target:return
        source=next((s for s in self.sources['feeds'] if s['url']==url),None)
        if not source:return
        if not items:
            self.source_errors[source['id']]='RSS poll returned no usable entries; existing baseline preserved'
            self.status();return
        rows=self._rows(source,items)
        added=self.inbox.ingest(url,session,rows)
        self.source_errors.pop(source['id'],None)
        poll_record={'source_id':source['id'],'url':url,'checked_at':datetime.now(timezone.utc).isoformat(),'rss_items':len(items),'candidate_rows':len(rows),'enqueued':len(added),'seen_urls':self.inbox.summary().get('seen_urls', 0)}
        with self.poll_log.open('a',encoding='utf-8') as log_file: log_file.write(json.dumps(poll_record,ensure_ascii=False)+'\n')
        logger.info('Market News poll source=%s rss_items=%d candidate_rows=%d enqueued=%d seen_urls=%d', source['id'], len(items), len(rows), len(added), poll_record['seen_urls'])
        if added:self.wake.set()
        self.status()

    async def _poll_now(self):
        rss=self._rss()
        if rss is None:raise RuntimeError('RSS plugin is not loaded')
        await asyncio.gather(*(rss.cron_task_callback(source['url'],self.target) for source in self.sources['feeds']))
        self.status()

    async def _control_loop(self):
        path=self.data_dir/'control.json'
        while True:
            try:
                if path.is_file():
                    request=json.loads(path.read_text(encoding='utf-8'))
                    request_id=str(request.get('id',''))
                    if not request_id.isalnum() or len(request_id)>64:raise ValueError('Invalid control request ID')
                    archived=self.data_dir/('control-'+request_id+'.json')
                    path.replace(archived)
                    action=request.get('action')
                    if action=='poll':
                        await self._poll_now();result={'status':'ok','summary':self.status()}
                    elif action=='test':
                        source=self.sources['feeds'][0]
                        _,_,_,rows=await asyncio.to_thread(self.collector.discover,source,self.sources)
                        chosen=next((row for row in rows if '国际黄金' in row['categories']),next((row for row in rows if row['categories']),None))
                        if not chosen:raise RuntimeError('No current fixed-source article available for test')
                        chosen['published_timestamp']=self.collector.parse_time(chosen['published_original']).timestamp() if self.collector.parse_time(chosen['published_original']) else 0
                        jobs=self.inbox.ingest(source['url'],self.target,[chosen],force_test=True);self.wake.set()
                        result={'status':'queued','job_ids':jobs,'test_label':'configuration verification, not a newly published article'}
                    else:raise ValueError('Unsupported control action')
                    (self.data_dir/('result-'+request_id+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                self.status()
            except asyncio.CancelledError:raise
            except Exception as exc:
                logger.error('Market News control error: %s',exc)
                if 'request_id' in locals() and request_id.isalnum():
                    (self.data_dir/('result-'+request_id+'.json')).write_text(json.dumps({'status':'failed','error':str(exc)[:300]},ensure_ascii=False),encoding='utf-8')
            await asyncio.sleep(5)

    async def _worker(self):
        while True:
            job=None
            try:
                job=self.inbox.next_job() if self.config.get('enabled') else None
                if job is None:
                    self.wake.clear()
                    try:await asyncio.wait_for(self.wake.wait(),timeout=10)
                    except asyncio.TimeoutError:pass
                    continue
                self.running=job['id'];self.status()
                await self._process(job)
            except asyncio.CancelledError:raise
            except Exception as exc:
                logger.error('Market News job failed: %s',exc,exc_info=True)
                if job:
                    current=self.inbox.db.execute('SELECT status,attempts FROM jobs WHERE id=?',(job['id'],)).fetchone()
                    if current and current['status']=='SENDING':self.inbox.update(job['id'],'UNKNOWN',error=type(exc).__name__+': '+str(exc)[:300])
                    elif current:
                        retry=current['attempts']<2
                        self.inbox.update(job['id'],'QUEUED' if retry else 'FAILED',error=type(exc).__name__+': '+str(exc)[:300],next_try=time.time()+60)
            finally:
                self.running=None;self.status()

    async def _process(self,job):
        payload=job['payload'];job_id=job['id']
        if job['status'] in ('RENDERED','BLOCKED_CONTEXT'):
            await self._deliver(job_id,job['report_path'],bool(payload.get('test_mode')))
            return
        if not payload.get('test_mode') and time.time()-job['created']>self.config.get('max_queue_age_minutes',120)*60:
            self.inbox.update(job_id,'EXPIRED',error='News exceeded processing queue age limit');return
        self.inbox.update(job_id,'RUNNING',claim=True)
        date=payload.get('date') or datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')
        source=next(s for s in self.sources['feeds'] if s['id']==payload['source_id'])
        article=payload.get('article')
        if not article or not article.get('text_path') or not (self.workspace/article['text_path']).is_file():
            attempt=job['attempts']+1
            batch=self.workspace/'data/raw'/date/(job_id+'-a'+str(attempt))
            for name in ('html','articles'):(batch/name).mkdir(parents=True,exist_ok=True)
            article=await asyncio.to_thread(self.collector.retrieve,payload,source,self.sources,batch)
            if article.get('content_level') not in ('full_text','partial_text','summary_only') or not article.get('text_path'):
                raise RuntimeError('Article body unavailable: '+str(article.get('error',article.get('content_level'))))
        paths={
            'event':f'runs/{date}/events/{job_id}.json',
            'processed':f'data/processed/{date}/{job_id}.md',
            'report':f'reports/{date}/{job_id}.md',
            'note':f'runs/{date}/{job_id}.md',
            'trace':f'runs/{date}/{job_id}-tools.json',
            'response':f'runs/{date}/{job_id}-response.md'}
        for relative in paths.values():(self.workspace/relative).parent.mkdir(parents=True,exist_ok=True)
        payload.update(article=article,date=date,paths=paths)
        self.inbox.db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(payload,ensure_ascii=False),job_id))
        (self.workspace/paths['event']).write_text(json.dumps({'job_id':job_id,'test_mode':payload.get('test_mode',False),'article':article,'outputs':{key:paths[key] for key in ('processed','report','note')}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        text=await asyncio.wait_for(run_editor(self.context,self.workspace,payload,paths),timeout=self.config.get('agent_timeout_seconds',600))
        if text is None:
            self.inbox.update(job_id,'SKIPPED',error='Agent judged article not suitable for this financial feed');return
        # The authoritative report file was written by the Agent, not regenerated here.
        self.inbox.update(job_id,'RENDERED',report_path=paths['report'])
        await self._deliver(job_id,paths['report'],bool(payload.get('test_mode')))

    async def _deliver(self,job_id,report_path,test_mode):
        platform_id,_,recipient=self.target.split(':',2)
        platform=self.context.get_platform_inst(platform_id)
        if platform is None or not getattr(platform,'token',None) or not getattr(platform,'_context_tokens',{}).get(recipient):
            self.inbox.update(job_id,'BLOCKED_CONTEXT',report_path=report_path,error='WeChat account/session context unavailable; user must refresh conversation',next_try=time.time()+60)
            return
        text=(self.workspace/report_path).read_text(encoding='utf-8').strip()
        if test_mode:text='【配置验证｜非新发布新闻】\n\n'+text
        self.inbox.update(job_id,'SENDING',report_path=report_path)
        accepted=await self.context.send_message(self.target,MessageChain(chain=[Comp.Plain(text)],use_t2i_=False))
        self.inbox.update(job_id,'ADAPTER_ACCEPTED' if accepted else 'FAILED',report_path=report_path,error=None if accepted else 'Target platform not found; message not submitted')

    @filter.command_group('market')
    def market(self):pass

    @market.command('status')
    async def market_status(self,event:AstrMessageEvent):
        if event.unified_msg_origin!=self.target:return
        status=self.status()
        yield event.plain_result('新闻监测已启用；每两分钟检查。\nRSS订阅：'+str(len(self.sources['feeds']))+'；网站：'+str(len({source['domains'][0] for source in self.sources['feeds']}))+'\n基线来源：'+str(len(status['feeds']))+'；暂停：'+str(len(status['paused_feeds']))+'\n任务状态：'+json.dumps(status['jobs'],ensure_ascii=False)+'\n当前任务：'+str(status['running_job']))

    @market.command('check')
    async def market_check(self,event:AstrMessageEvent):
        if event.unified_msg_origin!=self.target:return
        await self._poll_now()
        yield event.plain_result('已检查固定来源；仅新条目进入整理队列，不重复推送历史记录。')
