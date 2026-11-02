"""Real Chromium UI and interaction checks, with mocked in-browser HTTP responses.
Browser navigation to localhost is blocked by this environment's policy; backend API is tested separately.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parents[1]
js=(BASE/'static/app.js').read_text()
css=(BASE/'static/style.css').read_text()
html=(BASE/'static/index.html').read_text().replace('<link rel="stylesheet" href="/style.css"/>','').replace('<script defer src="/app.js"></script>','')
fake_fetch=r'''window.fakeCards=[];window.fakeAppointments=[];
window.fetch=async function(path, opts={}){
 const m=(opts.method||'GET').toUpperCase();const data=opts.body&&typeof opts.body==='string'?JSON.parse(opts.body):{};
 let out={};let status=200;
 if(path==='/api/session')out={guest:true,ai_configured:false};
 else if(path==='/api/cards')out={cards:window.fakeCards};
 else if(path==='/api/schedule')out={appointments:window.fakeAppointments,maintenance:[{card_id:'11111111111111111111111111111111',customer_name:'Demo Customer',start_date:'2026-11-19',maintenance_source:'Craftsman approved'}]};
 else if(path==='/api/appointments'&&m==='POST'){
  const id='abcde'+String(window.fakeAppointments.length+1).padStart(27,'0');window.fakeAppointments.push({...data,id,customer_name:null});out={id,saved:true};status=201;
 } else if(path.startsWith('/api/appointments/')&&m==='PUT'){
  const id=path.split('/')[3];const a=window.fakeAppointments.find(x=>x.id===id);Object.assign(a,data);out={id,saved:true};
 } else if(path.startsWith('/api/appointments/')&&m==='DELETE'){
  const id=path.split('/')[3];window.fakeAppointments=window.fakeAppointments.filter(a=>a.id!==id);out={deleted:true};
 } else if(path==='/api/events')out={saved:true};
 else throw new Error('Unexpected API call '+m+' '+path);
 return new Response(JSON.stringify(out),{status,headers:{'Content-Type':'application/json'}});
};'''
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':900})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html);page.add_style_tag(content=css);page.add_script_tag(content=fake_fetch);page.add_script_tag(content=js)
 page.get_by_role('button',name='Calendar').click()
 page.get_by_role('heading',name='Calendar').wait_for()
 assert page.locator('.calendar-day').count()==42
 page.get_by_role('button',name='New appointment').first.click()
 page.locator('#apt-title').fill('Heating annual inspection')
 page.locator('#apt-date').fill('2026-11-12')
 page.locator('#apt-time').fill('13:45')
 page.locator('#apt-notes').fill('Bring inspection tools')
 page.get_by_role('button',name='Save appointment').click()
 page.get_by_text('Appointment saved to your calendar.').wait_for()
 assert page.get_by_text('Heating annual inspection').count()>0
 page.screenshot(path='/mnt/data/customer-care-card-v4-calendar-desktop.png',full_page=True)
 page.get_by_role('button',name='Edit',exact=True).click()
 page.locator('#apt-time').fill('15:00')
 page.get_by_role('button',name='Save changes').click()
 page.get_by_text('15:00 · 60 min').wait_for(timeout=5000)
 page.locator('[data-cal-day="2026-11-19"]').click()
 assert page.get_by_text('Maintenance · Demo Customer').count()>0
 assert not errors,errors
 print('Browser desktop: 42-day calendar, create, edit, select maintenance, no JS errors — PASS')
 page.get_by_role('button',name='Edit',exact=True).count()
 page.get_by_role('button',name='Today').click()
 mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
 mobile_errors=[];mobile.on('pageerror',lambda e:mobile_errors.append(str(e)))
 mobile.set_content(html);mobile.add_style_tag(content=css);mobile.add_script_tag(content=fake_fetch);mobile.add_script_tag(content=js)
 mobile.get_by_role('button',name='Calendar').click()
 mobile.screenshot(path='/mnt/data/customer-care-card-v4-calendar-mobile.png',full_page=True)
 assert mobile.locator('.calendar-day').count()==42
 overflow=mobile.evaluate('document.documentElement.scrollWidth > window.innerWidth')
 assert not overflow,'Mobile horizontal overflow'
 assert not mobile_errors,mobile_errors
 print('Browser mobile: 42-day calendar, no overflow, no JS errors — PASS')
 browser.close()
