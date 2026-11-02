"""V7 end-to-end checks: update without customer picker, latest first, secure PDF import."""
import io,os,sys,tempfile,time,unittest,subprocess
from pathlib import Path
from pypdf import PdfReader
from test_integration import Client
BASE=Path(__file__).resolve().parents[1]

class CareCardUpdateV7(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='cc_v7_');cls.port=18779
  env={**os.environ,'DATA_DIR':cls.temp.name,'PORT':str(cls.port),'OPENAI_API_KEY':''}
  cls.proc=subprocess.Popen([sys.executable,str(BASE/'server.py')],cwd=BASE,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  cls.owner=Client(cls.port)
  for _ in range(100):
   try:
    if cls.owner.call('/api/health')[0]==200:break
   except Exception:time.sleep(.08)
  else:raise RuntimeError('V7 server did not start')
  cls.owner.call('/api/session')
 @classmethod
 def tearDownClass(cls):
  cls.proc.terminate();cls.proc.wait(timeout=5);cls.temp.cleanup()
 @staticmethod
 def payload(date,work):
  return {'business_name':'FixFlow Demo','business_contact':'demo@example.test','trade':'Plumbing / SHK','customer_name':'Mira Test','customer_address':'Berlin',
          'service_date':date,'product':'Shower pipe','problem':'Poor flow','work_done':work,'summary':work,
          'maintenance_date':'2027-02-10','maintenance_source':'Technician confirmed followup',
          'care_plan':{'priority':'Monitor shower pressure','routine_steps':['Check visible leaks'],'avoid':[],'warning_signs':[],'call_professional':[],'schedule':'Follow up 10 Feb','basis':'Technician note'},
          'approved':True,'upload_ids':[]}
 def test_01_create_pdf_resolve_update_pdf_history(self):
  cl=self.owner
  st,a=cl.call('/api/cards/create',self.payload('2026-10-21','ORIGINAL FIRST REPAIR: cleaned sediment'));self.assertEqual(st,201,a)
  id=a['id'];self.__class__.created_id=id
  st,pdf=cl.call('/api/cards/'+id+'/pdf');self.assertEqual(st,200)
  text=' '.join(x.extract_text() for x in PdfReader(io.BytesIO(pdf)).pages)
  self.assertIn('Card reference: '+id,text)
  st,up=cl.upload('my-original-care-card.pdf',pdf);self.assertEqual(st,200,up)
  st,match=cl.call('/api/cards/resolve',{'upload_id':up['files'][0]['id']});self.assertEqual(st,200,match)
  self.assertEqual(match['id'],id)
  st,work=cl.upload('new-visit.txt',b'New visit: installed filter. Checked visible leaks.',ctype='text/plain');self.assertEqual(st,200)
  payload=self.payload('2026-11-02','NEW SECOND VISIT: installed filter and checked leaks')
  payload['upload_ids']=[work['files'][0]['id']]
  st,updated=cl.call('/api/cards/'+id+'/visits',payload);self.assertEqual(st,200,updated)
  self.assertEqual(updated['id'],id)
  st,record=cl.call('/api/cards/'+id);self.assertEqual(st,200)
  visits=record['card']['visits'];self.assertEqual(len(visits),2)
  self.assertEqual(visits[0]['work_done'],'NEW SECOND VISIT: installed filter and checked leaks')
  self.assertEqual(visits[1]['work_done'],'ORIGINAL FIRST REPAIR: cleaned sediment')
  self.assertEqual(visits[0]['documents'][0]['filename'],'new-visit.txt')
  st,new_pdf=cl.call('/api/cards/'+id+'/pdf');self.assertEqual(st,200)
  self.assertNotEqual(pdf,new_pdf)
  updated_text=' '.join(p.extract_text() for p in PdfReader(io.BytesIO(new_pdf)).pages)
  self.assertIn('NEW SECOND VISIT',updated_text)
  self.assertIn('ORIGINAL FIRST REPAIR',updated_text)
  self.assertLess(updated_text.index('NEW SECOND VISIT'),updated_text.index('ORIGINAL FIRST REPAIR'))
  self.assertIn('2026-10-21',updated_text)
  self.assertIn('Mira Test',updated_text)
  self.assertIn('Card reference: '+id,updated_text)
  st,rem=cl.call('/api/cards/'+id+'/calendar');self.assertEqual(st,200);self.assertIn(b'BEGIN:VALARM',rem)
  st,new_upload=cl.upload('new-updated-card.pdf',new_pdf);self.assertEqual(st,200)
  self.assertEqual(cl.call('/api/cards/resolve',{'upload_id':new_upload['files'][0]['id']})[1]['id'],id)
 def test_02_owner_only_reference_and_legacy_error(self):
  ident=self.__class__.created_id
  other=Client(self.port);other.call('/api/session')
  self.assertEqual(other.call('/api/cards/resolve',{'reference':ident})[0],404)
  self.assertEqual(self.owner.call('/api/cards/resolve',{'reference':ident})[1]['id'],ident)
  status,msg=self.owner.call('/api/cards/resolve',{'reference':'ffffffff'*4})
  self.assertEqual(status,404)
  status,msg=self.owner.call('/api/cards/resolve',{'reference':'just a customer name'})
  self.assertEqual(status,400)
 def test_03_legacy_pdf_filename_recovers_reference(self):
  from reportlab.pdfgen.canvas import Canvas
  out=io.BytesIO();canvas=Canvas(out);canvas.drawString(50,750,'Legacy offline care card without an embedded reference');canvas.save()
  ident=self.__class__.created_id
  status,up=self.owner.upload('customer-care-guide-'+ident[:8]+'.pdf',out.getvalue());self.assertEqual(status,200)
  status,res=self.owner.call('/api/cards/resolve',{'upload_id':up['files'][0]['id']});self.assertEqual(status,200,res)
  self.assertEqual(res['id'],ident)
 def test_04_home_has_two_choices_no_customer_picker_or_calendar(self):
  st,content=self.owner.call('/app.js');self.assertEqual(st,200)
  src=content.decode('utf8')
  self.assertIn('Update an Existing Card',src)
  self.assertIn('Create a Care Card',src)
  line=next(x for x in src.splitlines() if x.startswith('const NAV='))
  self.assertNotIn('calendar',line.lower());self.assertNotIn('cards',line.lower())
  panel=src[src.index('function importPage()'):src.index('function monthMove(')]
  self.assertNotIn('existing-target',panel)
  self.assertNotIn('listing(',panel)

if __name__=='__main__':unittest.main()
