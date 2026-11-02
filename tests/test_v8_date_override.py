"""V8 maintenance override: card, visit, PDF, .ics, and account isolation."""
import io,os,sys,tempfile,time,unittest,subprocess
from pathlib import Path
from pypdf import PdfReader
from test_integration import Client
BASE=Path(__file__).resolve().parents[1]
class MaintenanceOverrideV8(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='care_v8_');cls.port=18812
  env={**os.environ,'DATA_DIR':cls.tmp.name,'PORT':str(cls.port),'OPENAI_API_KEY':''}
  cls.proc=subprocess.Popen([sys.executable,str(BASE/'server.py')],cwd=BASE,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  cls.owner=Client(cls.port)
  for _ in range(75):
   try:
    if cls.owner.call('/api/health')[0]==200:break
   except Exception:time.sleep(.07)
  else:raise RuntimeError('App not running')
  cls.owner.call('/api/session')
 @classmethod
 def tearDownClass(cls):cls.proc.terminate();cls.proc.wait(timeout=5);cls.tmp.cleanup()
 def test_01_date_change_controls_pdf_and_ics(self):
  payload={'business_name':'Demo Plumber','business_contact':'demo@example.test','trade':'Plumbing / SHK','customer_name':'Mira Demo',
    'service_date':'2026-10-29','product':'Shower pipe','work_done':'Removed shower sediment; verified water flow',
    'maintenance_date':'2027-01-29','maintenance_source':'Technician report recommended 3 months',
    'care_plan':{'priority':'Monitor water flow','routine_steps':['Check visible leaks'], 'avoid':[], 'warning_signs':[], 'call_professional':[], 'schedule':'Follow-up 29 January 2027','basis':'Work report'},'approved':True}
  st,data=self.owner.call('/api/cards/create',payload);self.assertEqual(st,201,data);cid=data['id'];self.__class__.id=cid
  status,changed=self.owner.call('/api/cards/'+cid+'/maintenance',{'maintenance_date':'2027-03-15'})
  self.assertEqual(status,200,changed)
  self.assertEqual(changed['card']['maintenance_date'],'2027-03-15')
  self.assertIn('Craftsperson selected',changed['card']['maintenance_source'])
  self.assertEqual(changed['card']['visits'][0]['maintenance_date'],'2027-03-15')
  self.assertIn('2027-03-15',changed['card']['visits'][0]['care_plan'])
  st,pdf=self.owner.call('/api/cards/'+cid+'/pdf');self.assertEqual(st,200)
  txt=' '.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
  self.assertIn('2027-03-15',txt);self.assertNotIn('2027-01-29',txt)
  st,ics=self.owner.call('/api/cards/'+cid+'/calendar');self.assertEqual(st,200)
  self.assertIn(b'20270315T090000',ics);self.assertNotIn(b'20270129T090000',ics)
  self.assertEqual(self.owner.call('/api/cards/'+cid)[1]['card']['maintenance_date'],'2027-03-15')
 def test_02_invalid_date_does_not_replace(self):
  st,res=self.owner.call('/api/cards/'+self.id+'/maintenance',{'maintenance_date':'2027-02-31'})
  self.assertEqual(st,400)
  self.assertEqual(self.owner.call('/api/cards/'+self.id)[1]['card']['maintenance_date'],'2027-03-15')
 def test_03_other_workspace_rejected(self):
  other=Client(self.port);other.call('/api/session')
  st,r=other.call('/api/cards/'+self.id+'/maintenance',{'maintenance_date':'2027-07-01'})
  self.assertIn(st,(403,404))
  self.assertEqual(self.owner.call('/api/cards/'+self.id)[1]['card']['maintenance_date'],'2027-03-15')
 def test_04_frontend_has_date_controls_and_independent_scrolling(self):
  st,content=self.owner.call('/app.js');self.assertEqual(st,200);s=content.decode()
  self.assertIn('id="chat-maintenance-date"',s);self.assertIn("a==='set-maintenance'",s)
  self.assertIn('id="f-maintenance_date"',s)
  st,css=self.owner.call('/style.css');self.assertEqual(st,200);styles=css.decode()
  self.assertIn('.create-layout > .editor-panel{min-height:0;overflow-y:auto',styles)
  self.assertIn('.ai-panel .chat-body{flex:1 1 100px',styles)
if __name__=='__main__':unittest.main()
