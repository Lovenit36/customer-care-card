"""Live HTTP integration checks using isolated temporary data; no API charges."""
import io,json,os,sys,tempfile,time,unittest,subprocess
from pathlib import Path
from urllib.request import build_opener,HTTPCookieProcessor,Request
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from pypdf import PdfReader
BASE=Path(__file__).resolve().parents[1]

class Client:
 def __init__(self,port):self.base=f'http://127.0.0.1:{port}';self.op=build_opener(HTTPCookieProcessor(CookieJar()))
 def call(self,path,payload=None,method=None,ctype=None):
  body=None if payload is None else(json.dumps(payload).encode() if not ctype else payload)
  r=Request(self.base+path,data=body,method=method or ('GET' if payload is None else 'POST'),headers={'Content-Type':ctype or 'application/json'})
  try:
   with self.op.open(r,timeout=20) as res:
    buf=res.read();return res.status,(json.loads(buf) if res.headers.get('Content-Type','').startswith('application/json') else buf)
  except HTTPError as e:
   buf=e.read();return e.code,json.loads(buf) if e.headers.get('Content-Type','').startswith('application/json') else buf
 def upload(self,name,data,ctype='application/pdf'):
  boundary='carecard_test_123'
  body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n').encode()+data+(f'\r\n--{boundary}--\r\n').encode()
  return self.call('/api/files',body,ctype=f'multipart/form-data; boundary={boundary}')

class EndToEnd(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='carecard_v3_');cls.port=18673
  env={**os.environ,'DATA_DIR':cls.tmp.name,'PORT':str(cls.port),'OPENAI_API_KEY':''}
  cls.proc=subprocess.Popen([sys.executable,str(BASE/'server.py')],cwd=BASE,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  cls.cl=Client(cls.port)
  for _ in range(70):
   try:
    if cls.cl.call('/api/health')[0]==200:break
   except Exception:time.sleep(.1)
  else:raise RuntimeError('server did not start')
 @classmethod
 def tearDownClass(cls):
  cls.proc.terminate();cls.proc.wait(timeout=5);cls.tmp.cleanup()
 def fields(self):
  return dict(business_name='Toms Plumbing',business_contact='toms@example.org',trade='Plumbing / SHK',
    customer_name='Raj',customer_address='Berlin',customer_phone='',service_date='2026-11-02',
    problem='Low shower pressure from heavy sediment',work_done='Removed dirt buildup, cleared shower pipe and tested for leaks',
    product='Shower pipe',findings='Dirt and sediment in pipe',materials='Replacement seal × 1',checks='Leak test passed',
    invoice_details='Labour €120, seal €20, total €140',unknowns='Pipe manufacturer unknown',
    source_references='invoice.pdf; report.txt',summary='Cleaned and repaired shower pipe.',
    aftercare='Technician recommends keeping shower area clean.',manual_url='',manual_evidence='',
    maintenance_date='2026-12-20',maintenance_source='Craftsman confirmed',warranty='',warranty_source='')
 def test_create_full_details_documents_pdf_and_alert(self):
  x=self.cl;self.assertEqual(x.call('/api/session')[0],200)
  st,doc=x.upload('report.txt',b'Shower pipe had excessive dirt and sediment; seal replaced; leak test passed.',ctype='text/plain');self.assertEqual(st,200,doc)
  doc_id=doc['files'][0]['id']
  st,r=x.call('/api/cards/create',{**self.fields(),'approved':True,'upload_ids':[doc_id]});self.assertEqual(st,201,r)
  card_id=r['id'];self.assertNotIn('customer_pin',r)
  st,record=x.call('/api/cards/'+card_id);self.assertEqual(st,200)
  visit=record['card']['visits'][0];self.assertEqual(visit['findings'],'Dirt and sediment in pipe');self.assertEqual(visit['invoice_details'],'Labour €120, seal €20, total €140')
  self.assertEqual(visit['documents'][0]['filename'],'report.txt')
  st,pdf=x.call('/api/cards/'+card_id+'/pdf');self.assertEqual(st,200);self.assertTrue(pdf.startswith(b'%PDF-'))
  text=' '.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
  for token in ['Dirt and sediment','Replacement seal','Labour','Leak test passed','Raj','Unknown / to verify']:
   self.assertIn(token,text)
  self.assertNotIn('Scan to access',text)
  st,calendar=x.call('/api/cards/'+card_id+'/calendar');self.assertEqual(st,200)
  self.assertIn(b'BEGIN:VALARM',calendar);self.assertIn(b'20261220T090000',calendar)
  st,newdoc=x.upload('new-observation.txt',b'Found minor sediment again; no leaks.',ctype='text/plain');self.assertEqual(st,200)
  new_id=newdoc['files'][0]['id']
  st,p=x.call('/api/cards/'+card_id+'/documents',{'upload_ids':[new_id]});self.assertEqual(st,200,p)
  st,record=x.call('/api/cards/'+card_id);self.assertEqual(len(record['card']['visits'][0]['documents']),2)
  fields=self.fields();fields.update(service_date='2027-01-10',work_done='Repeat flush of shower pipe',summary='Repeated pipe flush',findings='More dirt')
  st,r=x.call('/api/cards/'+card_id+'/visits',{**fields,'approved':True,'upload_ids':[]});self.assertEqual(st,200,r)
  st,record=x.call('/api/cards/'+card_id);self.assertEqual(len(record['card']['visits']),2)
  self.assertEqual(record['card']['visits'][1]['work_done'],'Removed dirt buildup, cleared shower pipe and tested for leaks')
  self.assertEqual(record['card']['visits'][0]['findings'],'More dirt')
  st,pdf=x.call('/api/cards/'+card_id+'/pdf');text=' '.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
  self.assertIn('Repeat flush',text);self.assertIn('cleared shower pipe',text.lower())
 def test_migrated_interface_and_deprecated_routes(self):
  x=self.cl;x.call('/api/session')
  for path in ('/api/wallet/status','/api/public/card/nope','/api/cards/'+'a'*32+'/qr','/api/cards/'+'a'*32+'/wallet'):
   self.assertEqual(x.call(path)[0],404,path)
  st,html=x.call('/');self.assertEqual(st,200)
  st,js=x.call('/app.js');self.assertEqual(st,200)
  self.assertIn(b'Customer Care Cards',js);self.assertNotIn(b'Customer access QR',js);self.assertNotIn(b'Add to Google Wallet',js)
 def test_isolation_and_validation(self):
  owner=Client(self.port);owner.call('/api/session');st,r=owner.call('/api/cards/create',{**self.fields(),'approved':True,'upload_ids':[]});self.assertEqual(st,201)
  id=r['id'];other=Client(self.port);other.call('/api/session')
  self.assertEqual(other.call('/api/cards/'+id)[0],404)
  self.assertEqual(other.call('/api/cards/'+id+'/documents',{'upload_ids':['a'*32]})[0],404)
  self.assertEqual(other.call('/api/cards/'+id,{},method='DELETE')[0],404)
  self.assertEqual(owner.call('/api/cards/'+id,{},method='DELETE')[0],200)
  self.assertEqual(owner.call('/api/cards/'+id)[0],404)
  self.assertEqual(owner.upload('bad.pdf',b'not-pdf')[0],400)
  self.assertEqual(owner.call('/api/cards/create',{'approved':True})[0],400)
 def test_ai_without_key_is_explicit(self):
  owner=Client(self.port);owner.call('/api/session')
  st,r=owner.call('/api/ai/draft',{'fields':{'work_done':'Cleared sediment'},'upload_ids':[]})
  self.assertEqual(st,502);self.assertIn('OPENAI_API_KEY',r['error'])
 def test_account_and_events(self):
  owner=Client(self.port);owner.call('/api/session')
  st,p=owner.call('/api/account',{'email':'unique-customer-v3@care.example','password':'correct horse battery stable'});self.assertEqual(st,200,p)
  relog=Client(self.port);relog.call('/api/session');self.assertEqual(relog.call('/api/login',{'email':'unique-customer-v3@care.example','password':'correct horse battery stable'})[0],200)
  self.assertEqual(owner.call('/api/events',{'event':'plancraft_cta_clicked','session_id':'testing_2026'})[0],201)
  self.assertEqual(owner.call('/api/events',{'event':'fake_signup','session_id':'testing_2026'})[0],400)
if __name__=='__main__':unittest.main()
