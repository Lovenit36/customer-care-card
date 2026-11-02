"""V8 simulated-backend Chromium visual and interaction checks. No private API calls."""
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parents[1]
html=(BASE/'static/index.html').read_text().replace('<link rel="stylesheet" href="/style.css"/>','').replace('<script defer src="/app.js"></script>','')
css=(BASE/'static/style.css').read_text();js=(BASE/'static/app.js').read_text()
mock='''
const CID='0123456789abcdef0123456789abcdef';
const PLAN={priority:'Monitor water flow',routine_steps:['Check for visible leaks'],avoid:[],warning_signs:[],call_professional:[],schedule:'29 Jan',basis:'Technician report'};
const V={service_date:'2026-11-02',product:'Shower pipe',problem:'Dirt',work_done:'Cleaned shower pipe',summary:'Pipe cleared',care_plan:JSON.stringify(PLAN),documents:[],created_at:'2026-11-02'};
const CARD={id:CID,customer_name:'Mira',business_name:'Klarfluss',business_contact:'test@example.com',trade:'Plumbing / SHK',product:'Shower pipe',maintenance_date:'2027-01-29',maintenance_source:'Technician note',visits:[V]};
window.fetch=async function(url,opts={}){
 let out={};
 if(url==='/api/session')out={guest:true,ai_configured:false};
 else if(url==='/api/cards')out={cards:[]};
 else if(url==='/api/schedule')out={appointments:[],maintenance:[]};
 else if(url==='/api/events')out={ok:true};
 else if(url==='/api/ai/draft')out={draft:{extracted_fields:{},summary:'Cleaned pipe',aftercare:'Monitor flow',manual_evidence:'',source_references:'work_report.pdf',maintenance_date:'2027-01-29',maintenance_source:'Work report',care_plan:{...PLAN,schedule:'29 January 2027'},warnings:''}};
 else if(url==='/api/cards/'+CID)out={card:CARD};
 else if(url==='/api/cards/'+CID+'/maintenance'){const d=JSON.parse(opts.body);CARD.maintenance_date=d.maintenance_date;CARD.maintenance_source='Craftsperson selected date (overrides documents)';V.maintenance_date=d.maintenance_date;PLAN.schedule='Next maintenance: '+d.maintenance_date;V.care_plan=JSON.stringify(PLAN);out={card:CARD};}
 else throw Error('Unexpected path '+url);
 return new Response(JSON.stringify(out),{headers:{'Content-Type':'application/json'}});
};'''
def boot(browser,width,height):
 page=browser.new_page(viewport={'width':width,'height':height})
 page.set_content(html);page.add_style_tag(content=css);page.add_script_tag(content=mock);page.add_script_tag(content=js)
 page.get_by_role('heading',name='Customer Care Card',exact=True).wait_for(timeout=5000)
 return page
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=boot(browser,1500,860)
 page.get_by_role('button',name='🪪 Create a new Care Card').click()
 page.wait_for_selector('#f-maintenance_date')
 base=page.evaluate('''() => {const b=document.body,f=document.querySelector('.editor-panel'),c=document.querySelector('.ai-panel'),cb=document.querySelector('.chat-body');return {body:b.scrollHeight,view:innerHeight,formScroll:f.scrollHeight,formClient:f.clientHeight,chatHeight:c.getBoundingClientRect().height,chatScroll:cb.scrollHeight,chatClient:cb.clientHeight,css:getComputedStyle(f).overflowY};}''')
 assert base['body']<=base['view']+4,base
 assert base['formScroll']>base['formClient']+150,base
 assert base['css']=='auto',base
 assert base['chatHeight']<base['view'],base
 page.locator('.editor-panel').evaluate('(el)=>el.scrollTop=600')
 assert page.locator('.editor-panel').evaluate('(el)=>el.scrollTop')>300
 page.locator('#f-maintenance_date').fill('2027-03-15');page.locator('#f-maintenance_date').dispatch_event('change')
 assert page.locator('#chat-maintenance-date').input_value()=='2027-03-15'
 page.locator('#chat-maintenance-date').fill('2027-04-18')
 page.get_by_role('button',name='Use this date').click()
 assert page.locator('#f-maintenance_date').input_value()=='2027-04-18'
 assert page.locator('#maintenance-source-note').inner_text().startswith('✅')
 page.locator('#ai-consent').check()
 page.get_by_role('button',name='Read documents & prepare care advice').click()
 page.get_by_text('AI draft ready').wait_for(timeout=5000)
 assert page.locator('#f-maintenance_date').input_value()=='2027-04-18'
 assert page.locator('#plan-schedule').input_value().startswith('Next maintenance: 2027-04-18')
 assert page.evaluate('document.body.scrollHeight <= window.innerHeight+4')
 page.screenshot(path=str(BASE/'v8-editor-desktop.png'))
 print('DESKTOP FORM',base)
 print('BEFORE_OPEN',flush=True);page.evaluate('openCard("0123456789abcdef0123456789abcdef")');print('AFTER_OPEN',flush=True)
 print('LEFT_SCROLL_BEFORE',page.locator('.result-layout > .stack').first.evaluate('(el)=>el.scrollTop'),flush=True);page.get_by_role('heading',name='Mira').wait_for(timeout=3000)
 page.get_by_role('button',name='Save date').wait_for()
 res=page.evaluate('''() => {const left=document.querySelector('.result-layout > .stack'),right=document.querySelector('.result-layout > .stack:last-child'),c=document.querySelector('.result-layout .ai-panel');return {leftHeight:left.clientHeight,leftScroll:left.scrollHeight,rightHeight:right.clientHeight,rightScroll:right.scrollHeight,chatHeight:c.clientHeight,body:document.body.scrollHeight,view:innerHeight};}''')
 assert res['body']<=res['view']+4,res
 assert res['leftScroll']>res['leftHeight'],res
 assert page.locator('.care-priority').is_visible()
 assert page.locator('.result-layout > .stack').first.evaluate('(el)=>el.scrollTop')==0
 assert res['chatHeight']<res['view'],res
 page.locator('#chat-maintenance-date').fill('2027-05-09');page.get_by_role('button',name='Save date').click()
 page.get_by_text('May 9, 2027').first.wait_for(timeout=3000)
 print('LEFT_SCROLL_AFTER',page.locator('.result-layout > .stack').first.evaluate('(el)=>el.scrollTop'),flush=True);page.screenshot(path=str(BASE/'v8-result-desktop.png'))
 print('DESKTOP RESULT',res)
 page.close()
 mobile=boot(browser,390,844)
 mobile.get_by_role('button',name='🪪 Create a new Care Card').click()
 mobile.wait_for_selector('#f-maintenance_date')
 assert mobile.locator('#f-maintenance_date').count()==1
 mobile.screenshot(path=str(BASE/'v8-editor-mobile.png'))
 browser.close()
 print('MOBILE OK')
print('V8 simulated browser tests passed')
