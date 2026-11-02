"""Project model permission errors should give actionable guidance, not a generic 502."""
import os,subprocess,sys,tempfile,time,socket,unittest,threading,json
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from test_integration import Client
BASE=Path(__file__).resolve().parents[1]

def freeport():
 with socket.socket() as sock:
  sock.bind(('127.0.0.1',0));return sock.getsockname()[1]
class Denied(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  payload=json.dumps({'error':{'message':"Project `proj_example` does not have access to model `gpt-6-sol`"}}).encode()
  self.send_response(403);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
class DenialTest(unittest.TestCase):
 def test_model_permission_error_is_readable(self):
  t=tempfile.TemporaryDirectory();port=freeport();aiport=freeport()
  fake=ThreadingHTTPServer(('127.0.0.1',aiport),Denied);threading.Thread(target=fake.serve_forever,daemon=True).start()
  env={**os.environ,'DATA_DIR':t.name,'PORT':str(port),'OPENAI_API_KEY':'placeholder_test_only',
       'OPENAI_MODEL':'gpt-6-sol','OPENAI_API_BASE_URL':f'http://127.0.0.1:{aiport}/v1'}
  p=subprocess.Popen([sys.executable,str(BASE/'server.py')],env=env,cwd=BASE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   c=Client(port)
   for _ in range(50):
    try:
     if c.call('/api/health')[0]==200:break
    except Exception:time.sleep(.1)
   c.call('/api/session');code,r=c.call('/api/ai/chat',{'question':'Summarise work done','upload_ids':[],'fields':{'work_done':'Shower pipe cleaned'},'thread':[]})
   self.assertEqual(code,502,r);self.assertIn('gpt-6-sol',r['error']);self.assertIn('allow this exact model',r['error']);self.assertIn('OPENAI_MODEL',r['error'])
  finally:
   p.terminate();p.wait(timeout=5);fake.shutdown();fake.server_close();t.cleanup()
if __name__=='__main__':unittest.main()
