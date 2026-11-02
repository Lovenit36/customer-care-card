"""Calendar CRUD, maintenance integration, permission checks and ICS tests."""
import os,sys,tempfile,time,unittest,socket,subprocess
from pathlib import Path
from test_integration import Client
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from schedule_logic import validate_appointment,schedule_ics
BASE=Path(__file__).resolve().parents[1]

def freeport():
 with socket.socket() as s:
  s.bind(('127.0.0.1',0));return s.getsockname()[1]

class Appointments(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.t=tempfile.TemporaryDirectory(prefix='care_v4_')
  cls.port=freeport()
  cls.env={**os.environ,'DATA_DIR':cls.t.name,'PORT':str(cls.port),'OPENAI_API_KEY':''}
  cls.proc=subprocess.Popen([sys.executable,str(BASE/'server.py')],env=cls.env,cwd=BASE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  cls.a=Client(cls.port)
  for _ in range(70):
   try:
    if cls.a.call('/api/health')[0]==200:break
   except Exception:time.sleep(.1)
  else:raise RuntimeError('Server not ready')
  cls.a.call('/api/session')
  cls.b=Client(cls.port);cls.b.call('/api/session')
 @classmethod
 def tearDownClass(cls):
  cls.proc.terminate();cls.proc.communicate(timeout=6);cls.t.cleanup()
 def payload(self,**kw):
  a=dict(title='Shower pipe check',start_date='2026-12-11',start_time='14:30',duration_minutes=60,notes='Test water flow',card_id=None)
  return a|kw
 def test_01_create_appointment_and_calendar_export(self):
  code,r=self.a.call('/api/appointments',self.payload())
  self.assertEqual(code,201,r);self.__class__.apt=r['id']
  code,calendar=self.a.call('/api/schedule');self.assertEqual(code,200)
  self.assertTrue(any(a['id']==self.apt and a['start_time']=='14:30' for a in calendar['appointments']))
  code,ics=self.a.call('/api/schedule/export');self.assertEqual(code,200)
  self.assertIn(b'DTSTART:20261211T143000',ics);self.assertIn(b'SUMMARY:Shower pipe check',ics)
  self.assertIn(b'TRIGGER:-PT30M',ics)
  self.assertEqual(self.a.call('/api/appointments/'+self.apt+'/calendar')[0],200)
 def test_02_edit_and_ownership(self):
  a=self.apt
  self.assertEqual(self.b.call('/api/appointments/'+a,self.payload(),method='PUT')[0],404)
  self.assertEqual(self.b.call('/api/appointments/'+a,{},method='DELETE')[0],404)
  self.assertEqual(self.b.call('/api/appointments/'+a+'/calendar')[0],404)
  code,r=self.a.call('/api/appointments/'+a,self.payload(start_date='2027-01-09',start_time='10:15',notes='Bring spare seal'),method='PUT');self.assertEqual(code,200,r)
  code,c=self.a.call('/api/schedule');item=next(a for a in c['appointments'] if a['id']==self.apt)
  self.assertEqual((item['start_date'],item['start_time'],item['notes']),('2027-01-09','10:15','Bring spare seal'))
  code,c2=self.b.call('/api/schedule');self.assertEqual(code,200);self.assertNotIn(self.apt,[a['id'] for a in c2['appointments']])
 def test_03_linked_care_card_maintenance_and_delete(self):
  fields=dict(business_name='Toms Plumbing',business_contact='shop@example.org',trade='Plumbing / SHK',customer_name='Raj',service_date='2026-11-02',
   work_done='Cleared sediment from shower pipe',maintenance_date='2026-12-20',maintenance_source='Confirmed by craftsman',approved=True,upload_ids=[])
  code,c=self.a.call('/api/cards/create',fields);self.assertEqual(code,201,c);card=c['id']
  code,c=self.a.call('/api/schedule');self.assertTrue(any(d['card_id']==card and d['start_date']=='2026-12-20' for d in c['maintenance']))
  code,r=self.a.call('/api/appointments',self.payload(card_id=card,start_date='2026-12-20'));self.assertEqual(code,201,r)
  aid=r['id']
  code,ics=self.a.call('/api/schedule/export');self.assertEqual(code,200)
  self.assertIn(b'Maintenance: Raj',ics);self.assertIn(b'appointment-'+aid.encode(),ics)
  self.assertIn(b'TRIGGER:-PT0M',ics)
  code,c=self.b.call('/api/appointments',self.payload(card_id=card));self.assertEqual(code,404)
  code,r=self.a.call('/api/cards/'+card,{},method='DELETE');self.assertEqual(code,200,r)
  code,c=self.a.call('/api/schedule');self.assertFalse(any(d['card_id']==card for d in c['maintenance']))
  self.assertIsNone(next(a for a in c['appointments'] if a['id']==aid)['card_id'])
 def test_04_validation_and_delete(self):
  for data in [self.payload(start_date='2026-02-29'),self.payload(start_time='25:00'),self.payload(title=''),self.payload(duration_minutes=10000),self.payload(card_id='invalid')]:
   status,r=self.a.call('/api/appointments',data);self.assertEqual(status,400,r)
  code,r=self.a.call('/api/appointments/'+self.apt,{},method='DELETE');self.assertEqual(code,200,r)
  self.assertNotIn(self.apt,[a['id'] for a in self.a.call('/api/schedule')[1]['appointments']])
  self.assertEqual(self.a.call('/api/appointments/'+self.apt+'/calendar')[0],404)
 def test_05_restart_persistence(self):
  code,r=self.a.call('/api/appointments',self.payload(title='Persistent follow-up',start_date='2027-02-17'))
  self.assertEqual(code,201,r);ident=r['id']
  self.proc.terminate();self.proc.wait(timeout=6)
  self.__class__.proc=subprocess.Popen([sys.executable,str(BASE/'server.py')],env=self.env,cwd=BASE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(70):
   try:
    code,c=self.a.call('/api/schedule')
    if code==200:break
   except Exception:time.sleep(.1)
  else:raise RuntimeError('Server not ready after restart')
  self.assertIn(ident,[a['id'] for a in c['appointments']])

class ScheduleValidation(unittest.TestCase):
 def test_date_time_and_ics_escaping(self):
  self.assertEqual(validate_appointment({'title':'Service','start_date':'2026-11-02','start_time':'09:00'})['duration_minutes'],60)
  output=schedule_ics({'appointments':[dict(id='abcdef',title='Fix, pipe; test',start_date='2026-11-02',start_time='08:15',duration_minutes=60,notes='One\nTwo')],'maintenance':[]})
  self.assertIn(b'Fix\\, pipe\\; test',output);self.assertIn(b'One\\nTwo',output)

if __name__=='__main__':unittest.main()
