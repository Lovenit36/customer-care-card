import unittest,sys,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from care_logic import generate_due,validate_care_input,determine_due_status,redact_pii
class DomainTests(unittest.TestCase):
 def test_month_end_leap(self):self.assertEqual(generate_due('2024-01-31',1),'2024-02-29')
 def test_maintenance_not_guessed(self):
  data=dict(business_name='A',business_contact='a@example.com',trade='Plumbing / SHK',customer_name='Max',service_date='2026-11-01',work_done='Changed tap',maintenance_date='2027-11-01')
  with self.assertRaises(ValueError):validate_care_input(data)
 def test_warranty_not_guessed(self):
  data=dict(business_name='A',business_contact='a@example.com',trade='Plumbing / SHK',customer_name='Max',service_date='2026-11-01',work_done='Changed tap',warranty='24 months')
  with self.assertRaises(ValueError):validate_care_input(data)
 def test_due(self):
  self.assertEqual(determine_due_status('2026-11-30',datetime.date(2026,11,1)),'soon')
  self.assertEqual(determine_due_status('2026-10-31',datetime.date(2026,11,1)),'overdue')
 def test_redaction(self):self.assertNotIn('test@example.com',redact_pii('email test@example.com'))
if __name__=='__main__':unittest.main()
