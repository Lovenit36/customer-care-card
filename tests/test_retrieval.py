import unittest
from retrieval import retrieve,format_evidence
class RetrievalTests(unittest.TestCase):
 def test_relevant_invoice_and_report_passages(self):
  docs=[{'source':'shower_invoice.pdf','text':'Invoice labour 120 EUR, seal 20 EUR, total 140 EUR. Payment due 22 December.'},
       {'source':'plumber_report.pdf','text':'The shower pipe had heavy sediment. The technician cleared the dirt, changed the seal and performed leak test.'},
       {'source':'unrelated.pdf','text':'Roof work gutter insulation on second floor.'}]
  got=retrieve(docs,'What caused the shower pipe blockage and what checks were performed?',limit=2)
  self.assertEqual(got[0]['source'],'plumber_report.pdf')
  self.assertIn('[Source: plumber_report.pdf]',format_evidence(got))
 def test_empty_and_no_cross_customer_sources(self):
  self.assertEqual(retrieve([],'invoice cost'),[])
  self.assertNotIn('other-customer',format_evidence(retrieve([{'source':'myfile','text':'My work'}],'work')))
if __name__=='__main__':unittest.main()
