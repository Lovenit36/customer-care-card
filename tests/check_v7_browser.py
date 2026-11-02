"""Playwright mock-browser verification. No API charges; no private customer data."""
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=Path(__file__).resolve().parents[1]
html=(BASE/'static/index.html').read_text().replace('<link rel="stylesheet" href="/style.css"/>','').replace('<script defer src="/app.js"></script>','')
css=(BASE/'static/style.css').read_text();js=(BASE/'static/app.js').read_text()
mock='''
const ID='0123456789abcdef0123456789abcdef';
const CARE={priority:'Monitor visible shower leaks',routine_steps:['Check water flow','Keep nozzles free of debris'],avoid:['Do not dismantle fittings'],warning_signs:['Low flow'],call_professional:['Recurring leaks'],schedule:'12 January',basis:'Technician note'};
const VISIT1={service_date:'2026-11-02',product:'Shower pipe',problem:'Low pressure',work_done:'New repair and replaced seal',summary:'New repair',care_plan:JSON.stringify(CARE),documents:[],created_at:'2026-11-02'};
const VISIT2={service_date:'2026-09-02',product:'Shower hose',problem:'Dripping',work_done:'Previous visit: checked hose',summary:'Previous repair',care_plan:JSON.stringify(CARE),documents:[],created_at:'2026-09-02'};
const CARD={id:ID,customer_name:'Mira Test',customer_address:'Berlin',business_name:'Demo Plumbing',business_contact:'demo@example.test',trade:'Plumbing / SHK',product:'Shower pipe',maintenance_date:'2027-01-12',maintenance_source:'Technician',visits:[VISIT1,VISIT2]};
window.fetch=async function(url,opts={}){let output={},status=200;
 if(url==='/api/session')output={guest:true,ai_configured:true};
 else if(url==='/api/cards')output={cards:[]};
 else if(url==='/api/schedule')output={appointments:[],maintenance:[]};
 else if(url==='/api/events')output={saved:true};
 else if(url==='/api/files')output={files:[{id:'f'.repeat(32),name:'existing-care-card.pdf',size:5000}]};
 else if(url==='/api/cards/resolve')output={id:ID};
 else if(url==='/api/cards/'+ID)output={card:CARD};
 else if(url==='/api/cards/'+ID+'/pdf')return new Response(new Blob(['%PDF-1.4\\n'],{type:'application/pdf'}),{headers:{'Content-Type':'application/pdf'}});
 else throw new Error('Unexpected fetch path '+url);
 return new Response(JSON.stringify(output),{status,headers:{'Content-Type':'application/json'}});
};
'''
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for width,height,label in [(1440,900,'desktop'),(390,844,'mobile')]:
  page=browser.new_page(viewport={'width':width,'height':height},accept_downloads=True)
  page.set_content(html)
  page.add_style_tag(content=css)
  page.add_script_tag(content=mock)
  page.add_script_tag(content=js)
  page.get_by_role('heading',name='Customer Care Card',exact=True).wait_for(timeout=5000)
  assert page.get_by_role('heading',name='Update an Existing Card').count()==1
  assert page.get_by_role('heading',name='Create a Care Card').count()==1
  assert page.locator('.nav button').count()==3
  assert not page.get_by_role('button',name='Calendar').count()
  page.get_by_role('button',name='🔄 Update an existing Care Card').click()
  assert page.get_by_role('heading',name='Update an Existing Care Card').count()==1
  assert not page.locator('#existing-target').count()
  assert not page.get_by_text('Or open a saved Customer Care Card').count()
  if label=='mobile':
   page.locator('#import-upload').set_input_files({'name':'original-care-card.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.4\n%%EOF'})
   page.get_by_text('existing-care-card.pdf').wait_for(timeout=4000)
  else:page.locator('#care-ref').fill('0123456789abcdef0123456789abcdef')
  page.get_by_role('button',name='🔄 Continue to new service').click()
  page.get_by_role('heading',name='Add a follow-up service').wait_for(timeout=4000)
  assert 'Mira Test' in page.locator('input#f-customer_name').input_value()
  page.screenshot(path=str(BASE/('v7-update-'+label+'.png')),full_page=True)
  page.close()
 # Check full result page (latest, history, download alert, no calendar)
 page=browser.new_page(viewport={'width':1440,'height':960},accept_downloads=True)
 page.set_content(html);page.add_style_tag(content=css);page.add_script_tag(content=mock);page.add_script_tag(content=js)
 page.get_by_role('button',name='🔄 Update an existing Care Card').click()
 page.locator('#care-ref').fill('0123456789abcdef0123456789abcdef')
 page.get_by_role('button',name='🔄 Continue to new service').click()
 page.evaluate("openCard('0123456789abcdef0123456789abcdef')")
 page.get_by_text('New repair',exact=False).wait_for(timeout=4000)
 assert page.get_by_text('Previous visit: checked hose').count() >= 1
 assert page.get_by_text('Download calendar alert').count() >= 1
 assert not page.get_by_role('button',name='Open calendar').count()
 with page.expect_download() as download_info:
  page.get_by_role('button',name='Download updated Care Card (PDF)').click()
 download=download_info.value
 assert download.suggested_filename.endswith('.pdf')
 page.screenshot(path=str(BASE/'v7-result-desktop.png'),full_page=True)
 page.close()
 browser.close()
print('V7 Chromium checks: desktop + mobile navigation, update by reference, latest and previous work, .ics, no calendar DB UI: PASSED')
