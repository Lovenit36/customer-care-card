"""Tests focused on V5 aftercare-first behaviour, safe structured plan, PDF and port."""
import io,json,os,sys,tempfile,unittest
from pathlib import Path
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from care_logic import normalize_care_plan, validate_care_input
from pdf_tools import card_pdf
BASE=Path(__file__).resolve().parents[1]

class CarePlanTests(unittest.TestCase):
 def plan(self):return {'priority':'Look for new leaks','routine_steps':['Keep visible nozzles clean','Monitor water pressure'], 'avoid':['Do not dismantle pipes'], 'warning_signs':['Low pressure returns'], 'call_professional':['Call if dripping returns'],'schedule':'Follow-up in three months if agreed','basis':'Service report; not a manufacturer manual'}
 def fields(self):return {'business_name':'Klarfluss Plumbing','business_contact':'service@example.org','trade':'Plumbing / SHK','customer_name':'Mira','service_date':'2026-11-02', 'work_done':'Removed dirt and replaced a seal','problem':'Poor water flow','findings':'Dirt and sediment build-up','checks':'No visible leak after test','invoice_details':'EUR 229.67 total','care_plan':self.plan(), 'maintenance_date':'2027-01-29','maintenance_source':'Craftsperson confirmed interval'}
 def test_normalise_and_validate(self):
  normalized=normalize_care_plan(self.plan());self.assertEqual(normalized['routine_steps'][0],'Keep visible nozzles clean')
  approved=validate_care_input(self.fields());self.assertEqual(approved['care_plan']['avoid'],['Do not dismantle pipes'])
  self.assertEqual(approved['maintenance_date'],'2027-01-29')
  self.assertRaises(ValueError,validate_care_input,self.fields()|{'maintenance_source':''})
  self.assertRaises(ValueError,normalize_care_plan,{'routine_steps':32})
 def test_readable_single_page_pdf(self):
  f=self.fields()
  card={**f,'id':'f'*32,'product':'Shower connection','customer_address':'Musterweg 12 Berlin'}
  visit={**f,'product':'Shower connection','summary':'Shower was repaired','care_plan':json.dumps(self.plan()),'source_references':'service_report.pdf and invoice.pdf','materials':'Replacement washer'}
  pdf=card_pdf(card,[visit]);r=PdfReader(io.BytesIO(pdf));text=' '.join(p.extract_text() for p in r.pages)
  self.assertEqual(len(r.pages),1,'Ordinary documented single repair should not create mostly empty extra page.')
  for word in ['HOW TO LOOK AFTER IT','SERVICE IN BRIEF','Keep visible nozzles clean','Dirt and sediment','229.67','2027-01-29','service_report.pdf']:
   self.assertIn(word,text)
 def test_old_record_without_structured_care(self):
  f=self.fields();card={**f,'id':'f'*32,'product':'Shower pipe','customer_address':'Berlin'}
  visit={**f,'aftercare':'Watch shower pressure','care_plan':''}
  pdf=card_pdf(card,[visit]);self.assertIn('Watch shower pressure',' '.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages))
 def test_port_and_safe_binding(self):
  src=(BASE/'server.py').read_text()
  self.assertIn("os.getenv('PORT','3000')",src)
  self.assertIn("os.getenv('HOST','127.0.0.1')",src)

if __name__=='__main__':unittest.main()
