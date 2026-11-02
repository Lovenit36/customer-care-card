"""Browser interaction and layout tests with simulated network responses. No live model key."""
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parents[1]
js=(BASE/'static/app.js').read_text();css=(BASE/'static/style.css').read_text();html=(BASE/'static/index.html').read_text().replace('<link rel="stylesheet" href="/style.css"/>','').replace('<script defer src="/app.js"></script>','')
api=r'''window.fakeCard=null;
window.fetch=async function(path, opts={}){
 let m=(opts.method||'GET').toUpperCase(),d=typeof opts.body==='string'?JSON.parse(opts.body):{},out={};let status=200;
 if(path==='/api/session')out={guest:true,ai_configured:true};
 else if(path==='/api/cards')out={cards:window.fakeCard?[window.fakeCard]:[]};
 else if(path==='/api/schedule')out={appointments:[],maintenance:[]};
 else if(path==='/api/ai/draft')out={draft:{summary:'Shower flow restored after sediment removal.',aftercare:'Keep external shower nozzles clean.',manual_evidence:'',maintenance_date:null,maintenance_source:null,warnings:'No manufacturer manual supplied.',source_references:'report.txt',extracted_fields:{business_name:'',business_contact:'',trade:'',customer_name:'',customer_address:'',service_date:'',problem:'Low pressure',work_done:'Removed sediment and replaced seal',product:'',findings:'Heavy sediment',materials:'Seal',checks:'Leak test',invoice_details:'EUR 229.67',unknowns:'Manufacturer unknown'},care_plan:{priority:'Watch for recurring pressure loss.',routine_steps:['Keep external shower nozzles clean','Check visible joints for drips','Note changes in pressure'],avoid:['Do not open concealed pipes'],warning_signs:['Water leaking','Low pressure returning'],call_professional:['If drips return'],schedule:'Follow-up date not confirmed',basis:'Technician report; manufacturer manual not supplied'}}};
 else if(path==='/api/cards/create'&&m==='POST'){window.fakeCard={...d,id:'11111111111111111111111111111111',visits:[{...d,care_plan:JSON.stringify(d.care_plan),documents:[]}],due_status:'not_set'};out={id:window.fakeCard.id};status=201;}
 else if(path==='/api/cards/11111111111111111111111111111111')out={card:window.fakeCard};
 else if(path==='/api/events')out={saved:true};
 else throw Error('unexpected: '+m+' '+path);
 return new Response(JSON.stringify(out),{status,headers:{'Content-Type':'application/json'}})
};'''
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1000})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html);page.add_style_tag(content=css);page.add_script_tag(content=api);page.add_script_tag(content=js)
 page.get_by_role('button',name='Create new →').click()
 page.get_by_text('1. Job essentials').wait_for()
 assert page.locator('.compact-editor .field:visible').count()==7
 page.locator('#f-business_name').fill('Klarfluss Plumbing')
 page.locator('#f-business_contact').fill('service@klarfluss.example')
 page.locator('#f-trade').select_option('Plumbing / SHK')
 page.locator('#f-customer_name').fill('Mira Becker')
 page.locator('#f-service_date').fill('2026-11-02')
 page.locator('#f-product').fill('Shower connection')
 page.locator('#ai-consent').check()
 page.get_by_role('button',name='Read documents & prepare care advice').click()
 page.get_by_text('AI draft ready — please check it.').wait_for()
 assert 'Watch for recurring pressure loss' in page.locator('#plan-priority').input_value()
 assert 'Removed sediment' in page.locator('#f-work_done').input_value()
 page.screenshot(path=str(BASE/'editor-v5.png'),full_page=True)
 page.locator('#approve').check()
 page.get_by_role('button',name='Create customer care card →').click()
 page.get_by_text('How to look after it').wait_for()
 assert page.get_by_text('Watch for recurring pressure loss.').count()>0
 assert page.get_by_text('What happened during the service?').count()>0
 assert page.get_by_text('3',exact=True).count()>0
 page.screenshot(path=str(BASE/'result-v5.png'),full_page=True)
 page.locator('[data-nav="calendar"]').click()
 page.locator('.calendar-day').first.wait_for()
 assert page.locator('.calendar-day').count()==42
 assert not errors,errors
 mobile=b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
 me=[];mobile.on('pageerror',lambda e:me.append(str(e)))
 mobile.set_content(html);mobile.add_style_tag(content=css);mobile.add_script_tag(content=api);mobile.add_script_tag(content=js)
 mobile.get_by_role('button',name='Create new →').click()
 mobile.screenshot(path=str(BASE/'mobile-v5.png'),full_page=True)
 assert mobile.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'),'Mobile horizontal overflow'
 assert not me,me
 print('Chromium simulated: compact form, AI draft, saved result, month calendar, mobile layout — PASS')
 b.close()
