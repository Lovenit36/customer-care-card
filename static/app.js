'use strict';
const $=sel=>document.querySelector(sel);
const $$=sel=>[...document.querySelectorAll(sel)];
const h=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nl=x=>h(x).replace(/\n/g,'<br>');
const niceDate=s=>s?new Date(s+'T12:00:00').toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'}):'Not recorded';
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
const FIELDS=['business_name','business_contact','trade','customer_name','customer_address','customer_phone','service_date','product','problem','work_done','findings','materials','checks','invoice_details','summary','aftercare','unknowns','source_references','manual_url','manual_evidence','maintenance_date','maintenance_source','warranty','warranty_source'];
const blank=()=>Object.fromEntries(FIELDS.map(k=>[k,'']));
const emptyPlan=()=>({priority:'',routine_steps:[],avoid:[],warning_signs:[],call_professional:[],schedule:'',basis:''});
const parsePlan=v=>{try{const o=typeof v==='string'?JSON.parse(v||'{}'):(v||{});return {...emptyPlan(),...o}}catch{return emptyPlan()}};

const state={page:'home',session:{},form:blank(),plan:emptyPlan(),files:[],importFiles:[],draft:null,current:null,cards:[],existingId:null,chat:[],busy:false,search:'',approve:false,metrics:[],notifs:false,schedule:{appointments:[],maintenance:[]},calendarMonth:today().slice(0,7),calendarDay:today(),appointmentForm:null,manualMaintenance:false};
const app=$('#app');
const NAV=[['home','🏠','Home'],['new','🪪','Create Care Card'],['existing','🔄','Update Existing Card']];
const PL='https://plancraft.com/en-gb/features?utm_source=customer_care_card&utm_medium=free_tool&utm_campaign=care_card_experiment';
const ses=(()=>{let s='';try{s=sessionStorage.getItem('cc_exp_session')||''}catch{}if(!s){s=crypto?.randomUUID?.().replaceAll('-','')||Math.random().toString(36).slice(2)+Date.now().toString(36);try{sessionStorage.setItem('cc_exp_session',s)}catch{}}return s})();
async function req(path,{method='GET',body,form=false}={}){
 const opts={method,credentials:'same-origin',headers:{}};
 if(body!==undefined){if(form)opts.body=body;else{opts.body=JSON.stringify(body);opts.headers['Content-Type']='application/json';}}
 let response;try{response=await fetch(path,opts)}catch{throw Error('Cannot connect to the server. Is python3 server.py running?')}
 const ct=response.headers.get('Content-Type')||'';
 if(!ct.includes('application/json')){if(!response.ok)throw Error('Server returned '+response.status);return response;}
 const payload=await response.json();if(!response.ok)throw Error(payload.error||'Request failed.');return payload;
}
function event(name){req('/api/events',{method:'POST',body:{event:name,session_id:ses}}).catch(()=>{});}
function snack(msg,error=false){$('.toast')?.remove();const el=document.createElement('div');el.className='toast';if(error)el.style.background='#a82a37';el.textContent=msg;document.body.appendChild(el);setTimeout(()=>el.remove(),6400);}
function fail(e){snack(e?.message||String(e),true);}
const btn=(label,action,cls='')=>`<button type="button" class="btn ${cls}" data-action="${action}">${label}</button>`;
const head=(heading,desc)=>`<div class="page-head"><h1>${heading}</h1><p>${desc}</p></div>`;
function footerCTA(){return `<section class="banner"><div><h3>Need to manage more than aftercare?</h3><p>Plancraft helps trade businesses handle ongoing admin. This free Customer Care Card app is an independent experiment, not an integrated Plancraft feature.</p><div class="benefits"><span>Quotes</span><span>Projects</span><span>Invoices</span><span>Customer data management</span><span>Customer history</span></div></div><a class="btn primary" id="pl-cta" href="${PL}" target="_blank" rel="noopener noreferrer">Explore Plancraft ↗</a></section>`;}
function shell(body){
 return `<header class="header"><div class="brand"><span class="brandmark">C</span><span>Customer Care Card</span></div><div class="header-right"><span class="pill">Free AI Tool</span><span class="avatar" title="Private craftsman workspace">${state.session.guest?'G':'✓'}</span></div></header>
 <div class="shell"><aside class="sidebar"><div class="nav">${NAV.map(([key,icon,name])=>`<button data-nav="${key}" class="${state.page===key?'active':''}"><span class="ni">${icon}</span>${name}</button>`).join('')}</div><div class="side-note">Save your Care Card reference and PDF for later updates.<br><strong>${state.session.guest?'Temporary browser session':'Saved business account'}</strong><br><a href="#account" data-nav="account">${state.session.guest?'Save your workspace':'Account settings'}</a></div></aside>
 <main class="main view-${state.page}">${body}${['home','cards'].includes(state.page)?footerCTA():''}<div class="footnote">For trade professionals. Review every AI-created fact before saving. Use fictional customer data for public demonstrations.</div></main></div>`;}
function field(key,label,{type='text',full=false,required=false,placeholder='',rows=3,desc='',choices=null}={}){
 const value=state.form[key]||'';let control=choices?`<select id="f-${key}">${['',...choices].map(x=>`<option value="${h(x)}" ${x===value?'selected':''}>${h(x||'Select trade…')}</option>`).join('')}</select>`:
 type==='textarea'?`<textarea id="f-${key}" rows="${rows}" placeholder="${h(placeholder)}">${h(value)}</textarea>`:`<input id="f-${key}" type="${type}" value="${h(value)}" placeholder="${h(placeholder)}">`;
 return `<div class="field ${full?'full':''}"><label for="f-${key}" ${required?'class="required"':''}>${label}</label>${control}${desc?`<small>${desc}</small>`:''}</div>`;
}
function getForm(){
 FIELDS.forEach(k=>{if($('#f-'+k))state.form[k]=$('#f-'+k).value.trim()});
 for(const k of Object.keys(emptyPlan())){const el=$('#plan-'+k);if(el){const v=el.value.trim();state.plan[k]=Array.isArray(emptyPlan()[k])?v.split('\n').map(x=>x.trim()).filter(Boolean):v;}}
 // Older manually entered guidance is preserved as a reviewed recommendation, not treated as a manufacturer instruction.
 if(!state.plan.routine_steps.length && state.form.aftercare)state.plan.routine_steps=[state.form.aftercare];
 if(state.manualMaintenance && state.form.maintenance_date){state.form.maintenance_source='Craftsperson selected date (overrides documents)';state.plan.schedule='Next maintenance: '+state.form.maintenance_date+' (craftsperson selected)';}
 return {...state.form,care_plan:state.plan};
}
function uploadedFiles(){return state.files.map(f=>`<div class="file-row"><span>▤</span><div class="fname"><strong>${h(f.name)}</strong><div class="tiny muted">${(f.size/1024).toFixed(0)} KB ${f.warning?'· '+h(f.warning):''}</div></div><span class="check">✓ Uploaded</span><button class="btn small ghost" data-remove="${f.id}">Remove</button></div>`).join('');}
function uploadBox(){return `<div class="upload-box"><div><div class="upload-title">📤 Upload work documents</div><div class="tiny muted">Invoices, reports, notes, product manuals or photos. 8 MB per file.</div></div><label class="btn small" for="upload">Choose files</label><input id="upload" class="hide" type="file" accept=".pdf,.docx,.txt,.md,.jpg,.jpeg,.png,.webp,.zip" multiple></div>${uploadedFiles()}`;}
function chatBox(onResult=false){return `<section class="panel ai-panel"><div class="panel-head">💬 &nbsp;Ask AI about this ${onResult?'customer record':'job'}</div>
 <div class="panel-body chat-intro"><p class="tiny muted">${onResult?'Reads approved service history and attached documents. AI requests share relevant record details with your configured provider.':'Ask about the notes and documents you are preparing.'} Answers reference available sources, not guesses.</p>
 ${onResult?`<label class="btn small" for="result-upload">📎 Attach a document</label><input id="result-upload" class="hide" type="file" multiple accept=".pdf,.docx,.txt,.md,.jpg,.jpeg,.png,.webp,.zip">`:''}
 <div class="quick-asks">${btn('Summarise history','ask-history','small')}${btn('Key work & costs','ask-costs','small')}${btn('What is missing?','ask-missing','small')}</div>
 ${onResult?`<div class="chat-maintenance"><label for="chat-maintenance-date">📅 Update next maintenance date</label><div class="chat-date-row"><input type="date" id="chat-maintenance-date" value="${h(state.current?.maintenance_date||'')}" aria-label="Choose maintenance date">${btn('Save date','set-maintenance','small primary')}</div><small>Saved to this card, its PDF and calendar alert.</small></div>`:`<div class="chat-maintenance"><label for="chat-maintenance-date">📅 Choose maintenance date (optional)</label><div class="chat-date-row"><input type="date" id="chat-maintenance-date" value="${h(state.form.maintenance_date||'')}" aria-label="Choose maintenance date">${btn('Use this date','set-maintenance','small primary')}</div><small>Your choice overrides the date from uploaded documents when you save the card.</small></div>`}
 </div>
 <div class="chat-body" id="chat-messages">${state.chat.length?state.chat.map(m=>`<div class="bubble ${m.by}">${nl(m.text)}${m.by==='ai'&&m.sources?.length?`<details class="chat-sources"><summary>Sources consulted (${m.sources.length})</summary><div>${m.sources.map(h).join('<br>')}</div></details>`:''}</div>`).join(''):'<div class="bubble ai">Ask about the repair, cost or next maintenance. I’ll give a short answer.</div>'}</div>
 <div class="chat-input"><input id="chat-question" placeholder="e.g. What was repaired during the last visit?" aria-label="Question about this record"><button class="btn primary" data-action="chat-send" ${state.busy?'disabled':''}>➜</button></div></section>`;}
function home(){return shell(`${head('Customer Care Card','Create a new care guide or add a dated visit to an existing card. No customer database to manage.')}
 <div class="two-cards"><section class="entry"><div class="entry-icon">🪪</div><h2>Create a Care Card</h2><p>Upload an invoice or work report and get a clear, practical aftercare guide.</p>${btn('🪪 Create a new Care Card →','new','primary big block')}</section>
 <section class="entry"><div class="entry-icon">🔄</div><h2>Update an Existing Card</h2><p>Upload a previously generated Care Card PDF, add the new work, and download an updated PDF. Earlier visits stay below.</p>${btn('🔄 Update an existing Care Card →','existing','big block')}</section></div>
 <div class="steps"><div class="step"><strong>1. Enter or upload</strong><p>Give the facts once, including any existing work documents.</p></div><div class="step"><strong>2. Review AI extraction</strong><p>Check reported problems, work, parts, invoices, dates and missing information.</p></div><div class="step"><strong>3. Keep a complete record</strong><p>Download the detailed offline PDF, chat with documents and track maintenance.</p></div></div>
 <div class="notice mt24">💡 Keep the downloaded Care Card PDF or its reference code. You’ll need it to add another visit later. To manage a full customer database, use Plancraft.</div>`);}
function planInput(key,title,{placeholder='',rows=2,small=false}={}){
 const value=state.plan[key];return `<div class="plan-edit ${small?'compact':''}"><label for="plan-${key}">${h(title)}</label><textarea id="plan-${key}" rows="${rows}" placeholder="${h(placeholder)}">${h(Array.isArray(value)?value.join('\n'):value)}</textarea>${Array.isArray(value)?'<small class="muted">One short recommendation per line.</small>':''}</div>`;
}
function editor(){return shell(`${head(state.existingId?'Add a follow-up service':'Create a Customer Care Card', 'Just the essentials. Upload an invoice or work report and let AI prepare the aftercare advice. You approve it before saving.')}
 ${state.existingId?`<div class="notice mb16"><strong>Adding a visit for ${h(state.form.customer_name)}</strong>. Earlier visits will remain in the history.</div>`:''}
 <div class="create-layout"><section class="panel editor-panel"><div class="panel-body compact-editor">
 <div class="section-label">📝 1. Job essentials</div><p class="tiny muted">Fill in what you know. Documents can provide the other details.</p>
 <div class="grid-form">
 ${field('business_name','Your business *',{required:true,placeholder:'e.g. Klarfluss Plumbing'})}
 ${field('business_contact','Your email or phone *',{required:true,placeholder:'Contact for follow-up'})}
 ${field('trade','Trade *',{required:true,choices:['Plumbing / SHK','Electrical','Painting','Carpentry','Roofing','Flooring','HVAC','Other']})}
 ${field('customer_name','Customer name or reference *',{required:true})}
 ${field('service_date','Date of work *',{type:'date',required:true})}
 ${field('product','What was serviced?',{placeholder:'e.g. Shower pipe (optional)'})}
 ${field('work_done','Quick work note',{type:'textarea',full:true,rows:2,placeholder:'Optional when your uploaded work report describes the completed repair.'})}
 </div>
 ${uploadBox()}
 <p class="micro">AI features send relevant details and uploaded files to your configured AI provider. Only use records you are authorised to share.</p>
 <div class="action-footer">${btn(state.busy?'Analysing documents…':'✦ Read documents & prepare care advice','draft','primary big')}${state.session.ai_configured?'':'<span class="tiny muted">AI requires an available API model; manual entry still works.</span>'}</div>
 ${state.draft?`<div class="notice mt16 ${state.draft.warnings?'warn':'ok'}"><strong>AI draft ready — please check it.</strong>${state.draft.warnings?`<p>${nl(state.draft.warnings)}</p>`:''}</div>`:'<p class="micro">AI reads attached files and creates a draft. Unsupported facts stay unconfirmed.</p>'}
 <div class="section-label mt24">🧰 2. Your customer’s care plan</div>
 <p class="section-note">This is the most important part of the card. Keep it helpful, short and safe. All guidance must be reviewed by the craftsperson.</p>
 ${planInput('priority','Most important advice',{placeholder:'e.g. Watch for recurring loss of shower pressure.'})}
 ${planInput('routine_steps','Simple maintenance steps',{placeholder:'Check the shower head for visible scale.\nMonitor water flow when showering.\nReport new leaks promptly.',rows:4})}
 <div class="grid-form plan-grid">
 ${planInput('avoid','What should the customer avoid?',{placeholder:'Leave concealed pipework to a professional.'})}
 ${planInput('warning_signs','Warning signs to watch for',{placeholder:'Recurring low pressure\nVisible leaks'})}
 ${planInput('call_professional','When to contact the craftsman',{placeholder:'Leaks that return\nUnusual pressure changes'})}
 ${planInput('schedule','When should maintenance happen?',{placeholder:'Only an evidenced date or interval'})}
 </div>
 <div class="maintenance-override"><div><strong>📅 Next maintenance date</strong><p>Use the documented date, or choose a different date. A date chosen here takes priority over AI extraction.</p></div>
 <div class="field"><label for="f-maintenance_date">Maintenance date (optional)</label><input id="f-maintenance_date" type="date" value="${h(state.form.maintenance_date||'')}"></div>
 <p class="micro" id="maintenance-source-note">${state.manualMaintenance?'✅ Date set by craftsperson — overrides documents.':state.form.maintenance_date?'📄 Suggested by uploaded documents; choose another date to override.':'No date is set. You can leave it blank.'}</p></div>
 <details class="optional-details"><summary>Review evidence, service details & warranty (optional)</summary><div class="grid-form mt16">
 ${field('customer_address','Property / service address')}${field('customer_phone','Customer phone')}
 ${field('problem','Reported issue',{type:'textarea',full:true,rows:2})}
 ${field('findings','What was found',{type:'textarea',full:true,rows:2})}
 ${field('materials','Parts and materials',{type:'textarea',full:true,rows:2})}
 ${field('checks','Checks performed',{type:'textarea',full:true,rows:2})}
 ${field('invoice_details','Invoice / payment',{type:'textarea',full:true,rows:2})}
 ${field('summary','Short service summary',{type:'textarea',full:true,rows:2})}
 ${field('aftercare','Additional approved guidance',{type:'textarea',full:true,rows:2})}
 ${field('unknowns','Not verified',{type:'textarea',full:true,rows:2})}
 ${field('source_references','Document references',{type:'textarea',full:true,rows:2})}

 ${field('warranty','Warranty terms')}${field('warranty_source','Warranty source')}
 ${field('manual_url','Manufacturer manual URL',{type:'url',full:true})}
 ${field('manual_evidence','Manual evidence',{type:'textarea',full:true,rows:2})}
 </div>${planInput('basis','Evidence behind the advice',{placeholder:'e.g. Technician report.pdf; general care advice not manufacturer verified',rows:2})}</details>
 <label class="approved"><input id="approve" type="checkbox" ${state.approve?'checked':''}><span>I have checked the facts and care advice and approve this card.</span></label>
 ${btn(state.existingId?'Save follow-up & view card →':'Create customer care card →','save-card','primary big block')}
 </div></section>${chatBox(false)}</div>`);}
function itemSection(title,content,empty='Not recorded in the available documents'){return `<section class="detail-section"><h4>${h(title)}</h4><p>${content?nl(content):`<span class="muted">${h(empty)}</span>`}</p></section>`;}
function allDocs(visits){return visits.flatMap(v=>(v.documents||[]).map(f=>({date:v.service_date,...f})));}
function adviceList(items,empty){return Array.isArray(items)&&items.length?`<ul class="care-list">${items.map(x=>`<li>${nl(x)}</li>`).join('')}</ul>`:`<p class="muted">${h(empty||'No confirmed instructions yet.')}</p>`;}
function result(){const c=state.current;if(!c)return shell(head('No card selected','Open a saved card first.'));
 const visits=c.visits||[],latest=visits[0]||{},docs=allDocs(visits),plan=parsePlan(latest.care_plan),steps=plan.routine_steps?.length?plan.routine_steps:(latest.aftercare?[latest.aftercare]:[]);
 return shell(`${head('Customer Care Card', 'Clear aftercare first, with the repair details and supporting documents available below.')}
 <div class="result-layout"><div class="stack"><section class="care-output">
 <div class="care-banner"><div><div class="care-eyebrow">🧰 YOUR AFTERCARE GUIDE</div><h2>${h(c.customer_name)}</h2><p>${h(c.product||c.trade||'Service')} · ${niceDate(latest.service_date)}</p></div><span class="care-symbol">🛠️</span></div>
 <div class="care-content"><div class="care-priority"><span>Most important</span><h3>${nl(plan.priority||'Follow your craftsperson’s recorded care advice.')}</h3></div>
 <h3 class="care-section-title">🧽 How to look after it</h3>
 ${steps.length?`<ol class="care-steps">${steps.map((x,i)=>`<li><span class="step-num">${i+1}</span><span>${nl(x)}</span></li>`).join('')}</ol>`:'<p class="muted">No maintenance steps have been confirmed yet. Ask the craftsperson for advice before using this as a guide.</p>'}
 <div class="care-cols"><div class="care-soft"><h4>⛔ What to avoid</h4>${adviceList(plan.avoid,'No product-specific restrictions recorded.')}</div><div class="care-soft"><h4>⚠️ Warning signs</h4>${adviceList(plan.warning_signs,'No specific warning signs recorded.')}</div></div>
 <div class="care-call"><h4>📞 When to call your craftsperson</h4>${adviceList(plan.call_professional,'For recurring problems or uncertainty, contact the servicing craftsperson.')}</div>
 <div class="care-schedule"><div><h4>📅 Next check or maintenance</h4><strong>${c.maintenance_date?niceDate(c.maintenance_date):h(plan.schedule||'Not scheduled')}</strong><p>${h(c.maintenance_source||'A confirmed maintenance interval has not been recorded.')}</p></div></div>
 <p class="care-basis"><strong>Advice source:</strong> ${nl(plan.basis||latest.manual_evidence||'Craftsperson-approved guidance. Manufacturer instructions not verified.')}</p>
 </div></section>
 <section class="service-simple"><div class="simple-header"><h2>🛠️ Latest work · ${niceDate(latest.service_date)}</h2><p>Customer: ${h(c.customer_name)} · Newest visit first; older history remains below.</p></div>
 <div class="service-meta"><span><strong>Craft business</strong>${h(c.business_name)}</span><span><strong>Contact</strong>${h(c.business_contact)}</span><span><strong>Service date</strong>${niceDate(latest.service_date)}</span><span><strong>Address</strong>${h(c.customer_address||'Not recorded')}</span></div>
 ${itemSection('The problem',latest.problem)}
 ${itemSection('What the craftsman did',latest.summary||latest.work_done)}
 ${itemSection('Parts, materials & checks',[latest.materials,latest.checks].filter(Boolean).join(' · '))}
 ${itemSection('Invoice / cost',latest.invoice_details)}
 ${latest.unknowns?itemSection('Still to be confirmed',latest.unknowns):''}
 <details class="optional-details"><summary>Technical notes, warranty & evidence</summary>
 ${itemSection('Technician findings',latest.findings)}${itemSection('Document references',latest.source_references)}${itemSection('Warranty',latest.warranty)}${itemSection('Warranty evidence',latest.warranty_source)}${itemSection('Manufacturer notes',latest.manual_evidence)}</details>
 <details class="optional-details" ${visits.length>1?'open':''}><summary>🗂️ Previous work (${Math.max(0,visits.length-1)} visit${visits.length===2?'':'s'})</summary>${visits.slice(1).map(v=>`<div class="older-visit"><h4>📅 ${niceDate(v.service_date)} · ${h(c.customer_name)} · ${h(v.product||'Service')}</h4><p><strong>Completed:</strong> ${nl(v.work_done||v.summary||'No details recorded')}</p>${v.problem?`<p><strong>Problem:</strong> ${nl(v.problem)}</p>`:''}${v.findings?`<p><strong>Findings:</strong> ${nl(v.findings)}</p>`:''}${v.materials?`<p><strong>Parts:</strong> ${nl(v.materials)}</p>`:''}${v.checks?`<p><strong>Checks:</strong> ${nl(v.checks)}</p>`:''}${v.invoice_details?`<p><strong>Invoice:</strong> ${nl(v.invoice_details)}</p>`:''}${v.aftercare?`<p><strong>Earlier advice:</strong> ${nl(v.aftercare)}</p>`:''}</div>`).join('')||'<p class="muted">This is the first recorded visit.</p>'}</details>
 <details class="optional-details"><summary>📎 Supporting documents (${docs.length})</summary>${docs.map(f=>`<div class="file-row"><span>▤</span><div class="fname">${h(f.filename)}</div><a class="btn small" target="_blank" rel="noopener noreferrer" href="/api/files/${f.id}?view=1">Open</a><a class="btn small" href="/api/files/${f.id}">Download</a></div>`).join('')||'<p class="muted">No documents attached.</p>'}</details>
 </section>
 <div class="action-footer">${btn('📄 Download updated Care Card (PDF)','pdf','primary')}${btn('➕ Add new work to this Card','update')}</div></div>
 <div class="stack">${chatBox(true)}<section class="panel"><div class="panel-head">📅 Maintenance reminder</div><div class="panel-body"><p>${c.maintenance_date?`Next recommended check: <strong>${niceDate(c.maintenance_date)}</strong>`:'No confirmed maintenance date.'}</p>${c.maintenance_date?`<a class="btn small" href="/api/cards/${c.id}/calendar">📥 Download calendar alert (.ics)</a>`:''}<p class="micro mt16">Import this file into Apple or Google Calendar to receive an alert. This is not a connected calendar service.</p></div></section><section class="panel"><div class="panel-head">🔄 Update this Card</div><div class="panel-body"><p class="tiny muted">Reference: <code>${h(c.id)}</code>. Save this code or the PDF for a future update.</p>${btn('➕ Record another visit','update','block')}</div></section>${footerCTA()}</div></div>`);}
function listing(title,items){return `<section class="panel"><div class="panel-head">${h(title)}</div><div class="panel-body">${items.length?`<div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Customer</th><th>Last visit</th><th>Next maintenance</th><th></th></tr></thead><tbody>${items.map(c=>`<tr><td><strong>${h(c.customer_name)}</strong><div class="tiny muted">${h(c.trade||'')}</div></td><td>${niceDate(c.service_date)}</td><td>${niceDate(c.maintenance_date)} <span class="tag ${c.due_status}">${h(c.due_status.replaceAll('_',' '))}</span></td><td>${btn('Open →','open-'+c.id,'small')}</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">No customer care cards saved yet. Create your first card or upload an existing work document.</div>'}</div></section>`;}
function cardsPage(){const items=state.cards.filter(c=>(c.customer_name+' '+c.trade).toLowerCase().includes(state.search.toLowerCase()));return shell(`${head('Customer Care Cards','All customer records, work history, documents and follow-up dates in one place.')}
 <input id="filter" class="search" placeholder="Search by customer or trade" value="${h(state.search)}">${listing('Saved Care Cards',items)}
 <div class="action-footer">${btn('＋ Create new card','new','primary')}${btn('↑ Open or import work documents','existing')}</div>`);}
function importPage(){return shell(`${head('🔄 Update an Existing Care Card','Upload the Care Card PDF you generated earlier, or paste its reference. Add any new repair documents on the next screen.')}
 <section class="panel update-only"><div class="panel-head">📄 Find your existing Care Card</div><div class="panel-body">
 <p class="muted">The reference is printed near the top of the downloaded PDF. You do not need to search a customer database.</p>
 <label class="field-label" for="care-ref">Card reference (optional if you upload the Care Card PDF)</label>
 <input id="care-ref" class="search" maxlength="40" placeholder="Paste the Care Card reference here">
 <div class="upload-box"><div><strong>📤 Upload previous Care Card PDF</strong><div class="tiny muted">Choose a PDF created by this app. Then click Continue.</div></div><label for="import-upload" class="btn small">Choose PDF</label><input id="import-upload" class="hide" type="file" accept=".pdf"></div>
 ${state.importFiles.map(f=>`<div class="file-row"><span>📄</span><strong>${h(f.name)}</strong><span class="check">✓ Uploaded</span></div>`).join('')}
 <div class="action-footer">${btn('🔄 Continue to new service →','resolve-existing','primary big block')}</div>
 <p class="micro">Older PDFs without a reference cannot always be matched automatically. If you already have the card open, choose “Add new work to this Card” instead.</p>
 </div></section>`);}
function monthMove(delta){const [y,m]=state.calendarMonth.split('-').map(Number);const d=new Date(y,m-1+delta,1);state.calendarMonth=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;}
function monthTitle(){const [y,m]=state.calendarMonth.split('-').map(Number);return new Date(y,m-1,1).toLocaleDateString(undefined,{month:'long',year:'numeric'});}
function scheduledEvents(){return [...state.schedule.appointments.map(a=>({...a,kind:'appointment',date:a.start_date,sort:a.start_time})),
 ...state.schedule.maintenance.map(m=>({...m,kind:'maintenance',date:m.start_date,sort:'09:00',title:'Maintenance · '+m.customer_name}))].sort((a,b)=>a.date.localeCompare(b.date)||a.sort.localeCompare(b.sort));}
const appointmentOptions=[15,30,45,60,90,120,180,240];
function calendarForm(){const f=state.appointmentForm||{};return `<section class="panel cal-editor"><div class="panel-head">${f.id?'Edit appointment':'New appointment'}</div><div class="panel-body">
 <div class="cal-form-grid"><div class="field full"><label for="apt-title">Appointment title *</label><input id="apt-title" maxlength="120" value="${h(f.title||'')}" placeholder="e.g. Shower repair visit"></div>
 <div class="field"><label for="apt-date">Date *</label><input type="date" id="apt-date" value="${h(f.start_date||state.calendarDay)}"></div>
 <div class="field"><label for="apt-time">Time *</label><input type="time" id="apt-time" value="${h(f.start_time||'09:00')}"></div>
 <div class="field"><label for="apt-duration">Duration</label><select id="apt-duration">${appointmentOptions.map(n=>`<option value="${n}" ${Number(f.duration_minutes||60)===n?'selected':''}>${n} min</option>`).join('')}</select></div>
 <div class="field"><label for="apt-card">Customer card (optional)</label><select id="apt-card"><option value="">No linked customer</option>${state.cards.map(c=>`<option value="${c.id}" ${f.card_id===c.id?'selected':''}>${h(c.customer_name)}</option>`).join('')}</select></div>
 <div class="field full"><label for="apt-notes">Visit notes (optional)</label><textarea id="apt-notes" rows="3" maxlength="2000" placeholder="Work requested or preparation notes">${h(f.notes||'')}</textarea></div></div>
 <div class="action-footer">${btn(f.id?'Save changes':'Save appointment','appointment-save','primary')}${btn('Cancel','appointment-cancel')}${f.id?btn('Delete','appointment-delete','danger'):''}</div>
 </div></section>`;}
function calendarPage(){const events=scheduledEvents(), appts=state.schedule.appointments,maintenance=state.schedule.maintenance;
 const [y,m]=state.calendarMonth.split('-').map(Number);const first=new Date(y,m-1,1);const offset=(first.getDay()+6)%7;
 const selected=events.filter(a=>a.date===state.calendarDay);const endOfMonth=new Date(y,m,0).getDate();
 const monthEvents=events.filter(a=>a.date.startsWith(state.calendarMonth));
 const grid=Array.from({length:42},(_,i)=>{const d=new Date(y,m-1,1-offset+i);const key=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
   const todays=events.filter(a=>a.date===key);return `<button type="button" class="calendar-day ${key===today()?'is-today':''} ${key===state.calendarDay?'is-selected':''} ${d.getMonth()!==m-1?'is-outside':''}" data-cal-day="${key}" aria-label="${h(niceDate(key))}, ${todays.length} events">
   <span class="calendar-day-num">${d.getDate()}</span><span class="calendar-events">${todays.slice(0,3).map(a=>`<span class="calendar-chip ${a.kind==='maintenance'?'maintenance-chip':'appointment-chip'}" title="${h(a.title)}">${h(a.kind==='appointment'?a.sort+' ':'')}${h(a.title)}</span>`).join('')}${todays.length>3?`<span class="calendar-more">+${todays.length-3} more</span>`:''}</span></button>`}).join('');
 return shell(`${head('Calendar','See every booked appointment and upcoming customer maintenance reminder in one place.')}
 <div class="calendar-toolbar"><div class="calendar-switch"><button class="btn small" data-action="cal-prev" aria-label="Previous month">←</button><h2>${h(monthTitle())}</h2><button class="btn small" data-action="cal-next" aria-label="Next month">→</button>${btn('Today','cal-today','small')}</div><div class="calendar-actions">${btn('＋ New appointment','appointment-new','primary')}<a class="btn" href="/api/schedule/export">↓ Export calendar (.ics)</a></div></div>
 <div class="calendar-layout"><section class="panel calendar-main"><div class="calendar-week">${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(x=>`<div>${x}</div>`).join('')}</div><div class="calendar-grid">${grid}</div><div class="calendar-legend"><span><i class="dot blue"></i> Appointments</span><span><i class="dot amber"></i> Maintenance</span><span>${monthEvents.length} event${monthEvents.length===1?'':'s'} this month</span></div></section>
 <div class="stack">${state.appointmentForm?calendarForm():`<section class="panel"><div class="panel-head">${h(niceDate(state.calendarDay))}</div><div class="panel-body"><div class="cal-agenda-title">${selected.length?selected.length+' scheduled event'+(selected.length===1?'':'s'):'Nothing scheduled'}</div>
 ${selected.length?selected.map(a=>`<article class="agenda-item ${a.kind==='maintenance'?'is-maintenance':''}"><div class="tiny muted">${a.kind==='appointment'?h(a.start_time)+' · '+a.duration_minutes+' min':'Maintenance reminder · 9:00 AM'}</div><strong>${h(a.title)}</strong>${a.customer_name&&a.kind==='appointment'?`<p class="tiny">${h(a.customer_name)}</p>`:''}${a.notes?`<p class="tiny">${h(a.notes)}</p>`:''}<div class="row">${a.kind==='appointment'?`${btn('Edit','appointment-edit-'+a.id,'small')} <a class="btn small" href="/api/appointments/${a.id}/calendar">Export alert ↓</a>`:`${btn('Open care card','open-'+a.card_id,'small')} <a class="btn small" href="/api/cards/${a.card_id}/calendar">Export alert ↓</a>`}</div></article>`).join(''):`<p class="muted tiny">Choose a date to view its events, or add a new appointment.</p>`}
 ${btn('＋ Add appointment on this day','appointment-new','block mt16')}</div></section>`}
 <section class="panel"><div class="panel-head">Reminders & notifications</div><div class="panel-body"><p class="tiny muted">Maintenance dates come from saved care cards. Appointments are saved separately and stay visible when you restart.</p>
 <div class="cal-counts"><span><strong>${appts.length}</strong> appointments</span><span><strong>${maintenance.length}</strong> maintenance dates</span></div>
 ${btn(state.notifs?'✓ Browser notifications on':'Enable browser notifications','enable-notifications','block')}
 <p class="micro mt16">Browser alerts require the app to be open. Export the calendar and import it into Apple or Google Calendar for alerts when the app is closed. Calendar exports are one-time snapshots, not live synchronization.</p></div></section>
 </div></div>`);}
function accountPage(){return shell(`${head('Save your workspace','Your care cards stay private to your account.')}
 <section class="panel" style="max-width:540px"><div class="panel-body">${state.session.guest?`<p>Currently a private browser session. Set an account password to keep your records when you return on another device.</p><div class="login"><label>Email<input id="email" type="email" autocomplete="email"></label><label>Password (12+ characters)<input id="password" type="password" autocomplete="new-password"></label>${btn('Save this workspace','claim','primary block')}</div><div class="line"></div><div class="login"><label>Existing account email<input id="login-email" type="email"></label><label>Password<input id="login-password" type="password"></label>${btn('Sign in','login','block')}</div>`:`<p>Signed in: ${h(state.session.email||'')}</p>${btn('Sign out','logout','danger')}`}</div></section>`);}
function render(){
 const selectors=['.main','.create-layout > .editor-panel','.create-layout > .ai-panel .chat-body','.result-layout > .stack:first-child','.result-layout > .stack:last-child','.result-layout .chat-body'];
 const positions=selectors.map(x=>document.querySelector(x)?.scrollTop||0);
 app.innerHTML=({home,create:editor,result,existing:importPage,account:accountPage}[state.page]||home)();bind();
 selectors.forEach((x,i)=>{const el=document.querySelector(x);if(el)el.scrollTop=positions[i];});
}
function bind(){
 $$('[data-nav]').forEach(el=>el.onclick=()=>el.dataset.nav==='new'?action('new'):go(el.dataset.nav));
 $$('[data-action]').forEach(el=>el.onclick=()=>action(el.dataset.action));
 $$('[data-cal-day]').forEach(el=>el.onclick=()=>{state.calendarDay=el.dataset.calDay;state.appointmentForm=null;render();});
 $$('[data-remove]').forEach(el=>el.onclick=()=>removeUpload(el.dataset.remove));
 $('#approve')?.addEventListener('change',e=>{state.approve=e.target.checked;});
 $('#f-maintenance_date')?.addEventListener('change',e=>{state.form.maintenance_date=e.target.value;state.manualMaintenance=Boolean(e.target.value);if(e.target.value){state.form.maintenance_source='Craftsperson selected date (overrides documents)';state.plan.schedule='Next maintenance: '+e.target.value+' (craftsperson selected)';} else {state.form.maintenance_source='';state.plan.schedule='';}const copy=$('#chat-maintenance-date');if(copy)copy.value=e.target.value;const info=$('#maintenance-source-note');if(info)info.textContent=e.target.value?'✅ Selected by craftsperson — overrides uploaded documents.':'No maintenance date selected.';});
 $('#upload')?.addEventListener('change',e=>upload(e.target,'create'));
 $('#import-upload')?.addEventListener('change',e=>upload(e.target,'import'));
 $('#result-upload')?.addEventListener('change',e=>upload(e.target,'result'));
 $('#chat-question')?.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();action('chat-send');}});
 $('#filter')?.addEventListener('input',e=>{state.search=e.target.value;const caret=e.target.selectionStart;render();$('#filter')?.focus();$('#filter')?.setSelectionRange(caret,caret);});
 $('#pl-cta')?.addEventListener('click',()=>event('plancraft_cta_clicked'));
}
async function refresh(){const r=await req('/api/cards');state.cards=r.cards||[];if(state.page==='calendar')await loadSchedule();checkNotifications();}
async function loadSchedule(){state.schedule=await req('/api/schedule');}
async function go(page){if(state.page==='create')getForm();state.page=page;state.chat=[];render();window.scrollTo(0,0);}
async function openCard(id,forUpdate=false){const d=await req('/api/cards/'+id);state.manualMaintenance=false;const card=d.card;state.current=card;state.chat=[];state.approve=false;
 state.form={...blank(),...Object.fromEntries(FIELDS.map(k=>[k,card[k]||''])),...(card.visits?.[0]||{})};
 state.plan=parsePlan(card.visits?.[0]?.care_plan);
 if(forUpdate){state.existingId=id;for(const k of ['product','problem','work_done','summary','aftercare','findings','materials','checks','invoice_details','unknowns','source_references','manual_evidence','maintenance_date','maintenance_source','warranty','warranty_source'])state.form[k]='';state.form.service_date=today();state.plan=emptyPlan();state.files=[];state.draft=null;state.page='create';}
 else{state.existingId=null;state.page='result';}render();window.scrollTo(0,0);}
async function upload(el,kind){const selected=[...el.files];if(!selected.length)return;if(selected.some(f=>f.size>8*1024*1024))return fail(Error('8 MB per file maximum.'));
 if(kind==='create')getForm();snack('Uploading '+selected.length+' file(s)…');try{
  const fd=new FormData();for(const f of selected)fd.append('file',f);const r=await req('/api/files',{method:'POST',body:fd,form:true});const files=r.files||[];
  if(kind==='import'){state.importFiles=files;}
  else if(kind==='result'){await req('/api/cards/'+state.current.id+'/documents',{method:'POST',body:{upload_ids:files.map(f=>f.id)}});const id=state.current.id;await openCard(id);snack('Document attached to this customer record. Ask AI about it.');return;}
  else state.files.push(...files);
  render();snack('Documents uploaded successfully. Continue with AI extraction.');
 }catch(e){fail(e)}}
async function removeUpload(id){try{if(state.page==='create')getForm();await req('/api/files/'+id,{method:'DELETE'});state.files=state.files.filter(f=>f.id!==id);render();snack('File removed.')}catch(e){fail(e)}}
async function chatSend(question){if(state.busy)return;
 const text=(question||$('#chat-question')?.value||'').trim();if(!text)return;
 if(state.page==='create')getForm();const thread=state.chat.slice(-10);state.chat.push({by:'me',text},{by:'ai',text:'Reading relevant documents…'});state.busy=true;render();
 try{const payload={question:text,fields:state.form,upload_ids:state.page==='create'?state.files.map(f=>f.id):[],card_id:state.page==='result'?state.current.id:state.existingId,thread};const r=await req('/api/ai/chat',{method:'POST',body:payload});
 state.chat[state.chat.length-1]={by:'ai',text:r.reply,sources:r.sources||[]};}
 catch(e){state.chat[state.chat.length-1]={by:'ai',text:'Error: '+e.message};}finally{state.busy=false;render();const body=$('#chat-messages');if(body)body.scrollTop=body.scrollHeight;}}
function NotificationAvailable(){return typeof Notification!=='undefined'&&('permission' in Notification);}
function checkNotifications(){if(!state.notifs||!NotificationAvailable()||Notification.permission!=='granted')return;const current=today();for(const c of state.cards.filter(x=>x.maintenance_date===current)){
 const key='cc_due_notification_'+c.id+'_'+current;try{if(localStorage.getItem(key))continue;new Notification('Maintenance due today',{body:`${c.customer_name}: maintenance follow-up`,tag:key});localStorage.setItem(key,'1');}catch(e){}}
 const d=new Date(),mins=d.getHours()*60+d.getMinutes();for(const a of state.schedule.appointments.filter(a=>a.start_date===current)){
 const [hour,min]=a.start_time.split(':').map(Number),until=hour*60+min-mins;if(until>30||until< -10)continue;
 const key='cc_appointment_'+a.id+'_'+current;try{if(localStorage.getItem(key))continue;new Notification('Appointment '+(until>0?'soon':'now'),{body:`${a.start_time} · ${a.title}`,tag:key});localStorage.setItem(key,'1');}catch(e){}}}
async function action(a){try{
 if(a==='set-maintenance'){
  const chosen=$('#chat-maintenance-date')?.value;
  if(!chosen)throw Error('Choose a maintenance date first.');
  if(state.page==='create'){
   getForm();state.form.maintenance_date=chosen;state.form.maintenance_source='Craftsperson selected date (overrides documents)';state.plan.schedule='Next maintenance: '+chosen+' (craftsperson selected)';state.manualMaintenance=true;
   render();snack('Maintenance date selected. Save the Care Card to confirm it.');return;
  }
  if(state.page==='result'&&state.current){
   const id=state.current.id;const r=await req('/api/cards/'+id+'/maintenance',{method:'POST',body:{maintenance_date:chosen}});
   state.current=r.card;await refresh();render();snack('Maintenance updated in Care Card, PDF and calendar alert.');return;
  }
  return;
 }

 if(a==='cal-prev'||a==='cal-next'){monthMove(a==='cal-prev'?-1:1);state.calendarDay=state.calendarMonth+'-01';state.appointmentForm=null;render();return;}
 if(a==='cal-today'){state.calendarMonth=today().slice(0,7);state.calendarDay=today();state.appointmentForm=null;render();return;}
 if(a.startsWith('calendar-for-')){state.calendarDay=a.slice('calendar-for-'.length);state.calendarMonth=state.calendarDay.slice(0,7);return await go('calendar');}
 if(a==='appointment-new'){state.appointmentForm={start_date:state.calendarDay,start_time:'09:00',duration_minutes:60,card_id:''};render();return;}
 if(a==='appointment-cancel'){state.appointmentForm=null;render();return;}
 if(a.startsWith('appointment-edit-')){const item=state.schedule.appointments.find(x=>x.id===a.slice('appointment-edit-'.length));if(!item)throw Error('Appointment not found.');state.appointmentForm={...item};render();return;}
 if(a==='appointment-save'){
  const data={title:$('#apt-title')?.value.trim(),start_date:$('#apt-date')?.value,start_time:$('#apt-time')?.value,
   duration_minutes:Number($('#apt-duration')?.value),card_id:$('#apt-card')?.value||null,notes:$('#apt-notes')?.value.trim()};
  const id=state.appointmentForm?.id;
  await req(id?'/api/appointments/'+id:'/api/appointments',{method:id?'PUT':'POST',body:data});
  state.appointmentForm=null;state.calendarDay=data.start_date;state.calendarMonth=data.start_date.slice(0,7);
  await loadSchedule();checkNotifications();render();snack(id?'Appointment updated.':'Appointment saved to your calendar.');return;
 }
 if(a==='appointment-delete'){
  const id=state.appointmentForm?.id;if(!id)return;
  if(!confirm('Delete this appointment? The customer care record will not be deleted.'))return;
  await req('/api/appointments/'+id,{method:'DELETE'});state.appointmentForm=null;
  await loadSchedule();render();snack('Appointment removed.');return;
 }
 if(a==='new'){state.page='create';state.existingId=null;state.current=null;state.form=blank();state.plan=emptyPlan();state.form.service_date=today();state.files=[];state.chat=[];state.approve=false;state.draft=null;state.manualMaintenance=false;render();event('tool_started');return;}
 if(['home','existing','account'].includes(a))return await go(a);
 if(a.startsWith('open-'))return await openCard(a.slice(5));
 if(a==='resolve-existing'){
  const reference=$('#care-ref')?.value.trim()||'';
  const pdf=state.importFiles[0];
  if(!reference&&!pdf)throw Error('Upload the previous Care Card PDF or enter its reference.');
  const result=await req('/api/cards/resolve',{method:'POST',body:{reference,upload_id:pdf?.id||null}});
  await openCard(result.id,true);state.importFiles=[];
  snack('Care Card found. Add the new work and documents, then save and download the updated PDF.');return;
 }
 if(a==='draft'){
  if(state.busy)return;const fields=getForm();state.busy=true;render();try{
   const r=await req('/api/ai/draft',{method:'POST',body:{fields,upload_ids:state.files.map(f=>f.id),card_id:state.existingId}});const draft=r.draft;state.draft=draft;
   const conflicting=['customer_name','service_date','trade','product'].filter(k=>draft.extracted_fields?.[k]&&state.form[k]&&draft.extracted_fields[k].toLowerCase().trim()!==state.form[k].toLowerCase().trim());
   if(conflicting.length)draft.warnings=(draft.warnings?draft.warnings+' ':'')+'Please check mismatches between entered information and document extraction: '+conflicting.join(', ')+'.';
   for(const [key,val] of Object.entries(draft.extracted_fields||{})){if(FIELDS.includes(key)&&!state.form[key]&&val)state.form[key]=val;}
   for(const key of ['summary','aftercare','manual_evidence','source_references']){if(draft[key])state.form[key]=draft[key];}
   if(draft.care_plan){state.plan=parsePlan(draft.care_plan);if(state.manualMaintenance&&state.form.maintenance_date)state.plan.schedule='Next maintenance: '+state.form.maintenance_date+' (craftsperson selected)';}
   if(draft.maintenance_date&&draft.maintenance_source&&!state.manualMaintenance&&!state.form.maintenance_date){state.form.maintenance_date=draft.maintenance_date;state.form.maintenance_source=draft.maintenance_source;}
   // Never copy a friendly AI summary into the confirmed-work field. Keep original evidence separate.
   event('ai_result_generated');snack('Details extracted. Check all fields before saving.');}
   catch(e){fail(e);}finally{state.busy=false;render();}return;
 }
 if(a==='save-card'){
  if(state.busy)return;const f=getForm();const missing=['business_name','business_contact','trade','customer_name','service_date','work_done'].filter(x=>!f[x]);if(missing.length)throw Error('Fill these required fields: '+missing.join(', '));
  if(!f.care_plan.routine_steps.length)throw Error('Add at least one approved step under Simple maintenance steps.');
  if(!state.approve)throw Error('Review the card and tick the approval checkbox.');if(f.maintenance_date&&!f.maintenance_source)throw Error('Explain the source of the maintenance date.');if(f.warranty&&!f.warranty_source)throw Error('Enter the warranty source.');
  state.busy=true;render();try{const endpoint=state.existingId?`/api/cards/${state.existingId}/visits`:'/api/cards/create';const r=await req(endpoint,{method:'POST',body:{...f,approved:true,upload_ids:state.files.map(x=>x.id)}});
  const wasUpdate=Boolean(state.existingId);await refresh();await openCard(r.id);state.files=[];event('result_used');snack(wasUpdate?'Updated Card saved with earlier history. Download its new PDF.':'New Care Card saved. Download the PDF to update it later.');}catch(e){fail(e)}finally{state.busy=false;render();}return;
 }
 if(a==='update')return openCard(state.current.id,true);
 if(a==='pdf'){
  const url='/api/cards/'+state.current.id+'/pdf';
  let response;try{response=await fetch(url,{credentials:'same-origin'});}catch{throw Error('Cannot reach the app server. Is it running on this port?')}
  if(!response.ok){let detail='PDF could not be generated.';try{const data=await response.json();detail=data.error||detail;}catch{}throw Error(detail+' Try again or check your server Terminal.');}
  if(!(response.headers.get('Content-Type')||'').includes('application/pdf'))throw Error('The server did not return a PDF. Check the Terminal logs.');
  const blob=await response.blob();const objectUrl=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=objectUrl;link.download='customer-care-guide-'+state.current.id.slice(0,8)+'.pdf';document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(objectUrl),10000);event('result_used');snack('Care guide downloaded.');return;
 }
 if(a==='delete-card'){if(!confirm('Permanently delete this Care Card and its service history?'))return;await req('/api/cards/'+state.current.id,{method:'DELETE'});state.current=null;await refresh();return go('home');}
 if(a==='chat-send')return await chatSend();
 if(a==='ask-history')return await chatSend('Summarise the previous service history with dates, work completed and sources.');
 if(a==='ask-costs')return await chatSend('List the confirmed work, parts and invoice amounts with their source documents.');
 if(a==='ask-missing')return await chatSend('Which important details are missing or unverified for this customer and what should the craftsman check?');
 if(a==='enable-notifications'){
  if(!NotificationAvailable())throw Error('This browser does not support notifications. Download the calendar event instead.');
  const perm=await Notification.requestPermission();state.notifs=perm==='granted';if(state.notifs)snack('Notifications enabled while this app is open.');else snack('Notification permission was not granted.',true);checkNotifications();render();return;
 }
 if(a==='claim'||a==='login'){const x=a==='login'?'login-':'';const email=$('#'+x+'email')?.value,password=$('#'+x+'password')?.value;await req(a==='claim'?'/api/account':'/api/login',{method:'POST',body:{email,password}});state.session=await req('/api/session');await refresh();snack('Account ready.');return go('cards');}
 if(a==='logout'){await req('/api/logout',{method:'POST',body:{}});state.session=await req('/api/session');return go('home');}
 }catch(e){fail(e);}}
async function init(){try{state.notifs=NotificationAvailable()&&Notification.permission==='granted';state.session=await req('/api/session');await refresh();await loadSchedule();checkNotifications();render();event('landing_view');setInterval(()=>{refresh().then(()=>loadSchedule()).then(()=>checkNotifications()).catch(()=>{})},60000);}catch(e){app.innerHTML=`<main class="startup"><h1>Unable to open Customer Care Card</h1><p>${h(e.message)}</p><p>Start with <code>python3 server.py</code>.</p></main>`;}}
init();
