"""End-to-end request/structured extraction tests with a local simulated Responses API.
This does not make a paid model request; actual model access must be tested by user.
"""
import io,json,os,sys,threading,tempfile,subprocess,time,unittest,socket
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from test_integration import Client
BASE=Path(__file__).resolve().parents[1]

def freeport():
 with socket.socket() as sock:
  sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

class FakeAI(BaseHTTPRequestHandler):
 seen=[]
 def log_message(self,*args):pass
 def do_POST(self):
  incoming=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  FakeAI.seen.append(incoming)
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
  if incoming.get('text',{}).get('format',{}).get('type')=='json_schema':
   props=incoming['text']['format']['schema']['properties']['extracted_fields']['properties']
   extracted={k:'' for k in props}
   extracted.update({'customer_name':'Raj','service_date':'2026-11-02','problem':'Low shower pressure',
     'work_done':'Cleared shower pipe and removed sediment','findings':'Heavy sediment',
     'materials':'Replacement seal','checks':'Water flow checked','invoice_details':'140 EUR total'})
   content=dict(summary='Shower pipe repaired and flow checked.',aftercare='Technician advises monitoring flow.',
     manual_evidence='',maintenance_date=None,maintenance_source=None,warnings='Product make not verified.',
     source_references='shower_report.txt',extracted_fields=extracted,
     care_plan=dict(priority='Monitor shower pressure',routine_steps=['Keep nozzles clean','Watch for low flow'],avoid=['Do not open pipes'],warning_signs=['Leaks'],call_professional=['When pressure drops again'],schedule='No confirmed interval',basis='shower_report.txt'))
   output=json.dumps(content)
  else:output='Shower report records removal of heavy sediment [shower_report.txt]. Earlier visit noted a pipe repair [Saved visit 2026-11-02].'
  self.wfile.write(json.dumps({'output':[{'content':[{'type':'output_text','text':output}]}]}).encode())

class AIServerTest(unittest.TestCase):
 def test_document_extraction_and_saved_history_retrieval(self):
  tmp=tempfile.TemporaryDirectory();port=freeport();modelport=freeport();FakeAI.seen=[]
  fake=ThreadingHTTPServer(('127.0.0.1',modelport),FakeAI)
  t=threading.Thread(target=fake.serve_forever,daemon=True);t.start()
  env={**os.environ,'DATA_DIR':tmp.name,'PORT':str(port),'OPENAI_API_KEY':'unit-test-secret',
        'OPENAI_MODEL':'fake-gpt-sol','OPENAI_API_BASE_URL':f'http://127.0.0.1:{modelport}/v1'}
  proc=subprocess.Popen([sys.executable,str(BASE/'server.py')],env=env,cwd=BASE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   x=Client(port)
   for _ in range(50):
    try:
     if x.call('/api/health')[0]==200:break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('Server not ready')
   x.call('/api/session')
   st,u=x.upload('shower_report.txt',b'Raj shower pipe blocked by heavy sediment. Removed sediment, replaced seal, total 140 EUR.',ctype='text/plain')
   self.assertEqual(st,200,u);docid=u['files'][0]['id']
   st,draft=x.call('/api/ai/draft',{'fields':{},'upload_ids':[docid]})
   self.assertEqual(st,200,draft)
   self.assertEqual(draft['draft']['extracted_fields']['work_done'],'Cleared shower pipe and removed sediment')
   self.assertIn('shower_report.txt',json.dumps(FakeAI.seen[-1]))
   self.assertEqual(FakeAI.seen[-1]['model'],'fake-gpt-sol')
   base=dict(business_name='Toms Plumbing',business_contact='toms@example.org',trade='Plumbing / SHK',
    customer_name='Raj',service_date='2026-11-02',work_done='Removed sediment and replaced seal',
    findings='Heavy sediment',approved=True,upload_ids=[docid])
   st,created=x.call('/api/cards/create',base);self.assertEqual(st,201,created)
   cardid=created['id'];st,chat=x.call('/api/ai/chat',{
      'question':'What is known about the prior pipe blockage and invoice?',
      'upload_ids':[],'card_id':cardid,'fields':{},'thread':[{'by':'me','text':'Tell me the history'}]})
   self.assertEqual(st,200,chat);self.assertIn('shower_report.txt',chat['sources'])
   sent=json.dumps(FakeAI.seen[-1]);self.assertIn('Saved visit 2026-11-02',sent);self.assertIn('sediment',sent.lower())
   self.assertEqual(st,200)
  finally:
   proc.terminate();proc.wait(timeout=5);fake.shutdown();fake.server_close();tmp.cleanup()
if __name__=='__main__':unittest.main()
