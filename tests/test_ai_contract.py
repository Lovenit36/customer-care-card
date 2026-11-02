import io,json,os,sys,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class TestAIContract(unittest.TestCase):
 def test_structured_response_api_shape_and_parser(self):
  body={"output":[{"content":[{"type":"output_text","text":json.dumps({
   'summary':'A valve was replaced.','aftercare':'No product manual provided.',
   'manual_evidence':'','maintenance_date':None,'maintenance_source':None,'warnings':'No documented interval.'
  })}]}]}
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self):return json.dumps(body).encode()
  inspected=[]
  def fake_urlopen(request,timeout):
   args=json.loads(request.data);inspected.append(args)
   self.assertEqual(args['text']['format']['type'],'json_schema')
   self.assertEqual(args['text']['format']['strict'],True)
   self.assertEqual(args['input'][0]['content'][0]['type'],'input_text')
   self.assertTrue(request.full_url.endswith('/responses'))
   return Response()
  with patch.dict(os.environ,{'OPENAI_API_KEY':'test-key-only-never-sent','OPENAI_MODEL':'gpt-4.1-mini'}), patch.object(server,'urlopen',fake_urlopen):
   result=server.openai_answer('Use evidence only','Replaced valve',server.DRAFT_SCHEMA)
  self.assertEqual(result['summary'],'A valve was replaced.')
  self.assertIsNone(result['maintenance_date'])
  self.assertEqual(len(inspected),1)
if __name__=='__main__':unittest.main()
