"""Chromium UI regression check for concise chat and safe PDF download.
Network is deliberately mocked; no external API requests or user data.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parents[1]
html=(BASE/'static/index.html').read_text().replace('<link rel="stylesheet" href="/style.css"/>','').replace('<script defer src="/app.js"></script>','')
css=(BASE/'static/style.css').read_text()
js=(BASE/'static/app.js').read_text()
mock=r'''
window.failPDF=false;
const ID='11111111111111111111111111111111';
const VISIT={service_date:'2026-11-03',product:'Shower pipe',problem:'Low pressure',work_done:'Flushed and replaced seal',summary:'Repaired shower connection',care_plan:JSON.stringify({priority:'Monitor the flow',routine_steps:['Check visible leaks'],avoid:[],warning_signs:['Low pressure'],call_professional:[],schedule:'No set date',basis:'Technician report'}),documents:[]};
const CARD={id:ID,customer_name:'Mira',business_name:'Toms',business_contact:'test@example.com',product:'Shower pipe',trade:'Plumbing',service_date:'2026-11-03',maintenance_date:'',visits:[VISIT]};
window.fetch=async function(url,options={}){
 let status=200,output={};
 if(url==='/api/session')output={guest:true,ai_configured:true};
 else if(url==='/api/cards')output={cards:[{id:ID,customer_name:'Mira',trade:'Plumbing',service_date:'2026-11-03',maintenance_date:'',due_status:'not_set'}]};
 else if(url==='/api/schedule')output={appointments:[],maintenance:[]};
 else if(url==='/api/cards/'+ID)output={card:CARD};
 else if(url==='/api/ai/chat')output={reply:'Sediment reduced shower flow. A worn seal caused dripping. Both were repaired.',sources:['report.pdf','Saved visit 2026-11-03']};
 else if(url==='/api/cards/'+ID+'/pdf'){
    if(window.failPDF){status=500;output={error:'PDF could not be generated.'}}
    else return new Response(new Blob(['%PDF-1.4\n%%EOF'],{type:'application/pdf'}),{status:200,headers:{'Content-Type':'application/pdf'}})
 }
 else if(url==='/api/events')output={saved:true};
 else throw Error('Unexpected call '+url);
 return new Response(JSON.stringify(output),{status,headers:{'Content-Type':'application/json'}});
};
'''
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1400,'height':900},accept_downloads=True)
 errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
 page.set_content(html);page.add_style_tag(content=css);page.add_script_tag(content=mock);page.add_script_tag(content=js)
 page.locator('[data-nav=cards]').click();page.locator('[data-action^="open-"]').click()
 page.locator('#chat-consent').check()
 page.locator('#chat-question').fill('In short, what happened?')
 page.locator('[data-action=chat-send]').click()
 page.get_by_text('Sediment reduced shower flow.',exact=False).wait_for()
 assert page.locator('.chat-sources').count()==1
 assert not page.locator('.chat-sources').first.evaluate('(e)=>e.open'), 'Sources should be hidden by default'
 assert page.locator('.chat-body').inner_text().count('Sources:')==0
 page.locator('.chat-sources summary').click()
 assert 'report.pdf' in page.locator('.chat-sources').inner_text()
 page.screenshot(path=str(BASE/'chat-v6-preview.png'),full_page=False)
 with page.expect_download(timeout=5000) as dl:
  page.locator('[data-action=pdf]').click()
 download=dl.value
 assert download.suggested_filename.startswith('customer-care-guide-')
 page.evaluate('window.failPDF=true')
 page.locator('[data-action=pdf]').click()
 page.get_by_text('PDF could not be generated.',exact=False).wait_for()
 assert page.url=='about:blank', 'PDF error should not navigate away from the Care Card'
 assert not errs,errs
 print('V6 Chromium checks: short chat, collapsed sources, download link, PDF error handling — PASS')
 b.close()
