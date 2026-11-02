"""Regressions from V5: too-long chat text and PDF 500 on real descriptions."""
import io
import json
import os
import sys
import tempfile
import time
import socket
import subprocess
import unittest
from pathlib import Path
from pypdf import PdfReader
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from pdf_tools import card_pdf
from server import short_chat_reply
from test_integration import Client


def freeport():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]

class V6Regression(unittest.TestCase):
    def sample(self):
        card={
          'id':'1'*32,'business_name':'Klarfluss Plumbing',
          'customer_name':'Mira Becker','trade':'Plumbing / SHK',
          'product':'Shower supply pipe','service_date':'2026-11-03',
          'business_contact':'test@example.org','customer_address':'Berlin',
          'maintenance_date':'2027-01-29','maintenance_source':'Technician recommended'}
        plan={
          'priority':'Check for sediment reappearing. Do not dismantle components.',
          'routine_steps':['Clean only accessible shower nozzles','Check visible leaks and water flow'],
          'avoid':['Do not open sealed fittings'],
          'warning_signs':['Water pressure dropping again'],
          'call_professional':['If leaks or pressure problems return'],
          'schedule':'Next approved check 29 January 2027',
          'basis':'Technician work report'}
        visit={'service_date':'2026-11-03','product':'Shower pipe',
               'care_plan':json.dumps(plan),'problem':'Low pressure and dripping',
               'work_done':'Replaced seal and flushed connection.','findings':'Heavy sediment',
               'invoice_details':'EUR 229.67', 'source_references':'work_report.pdf'}
        return card,visit

    def test_long_pdf_does_not_raise_layout_error(self):
        card,visit=self.sample()
        for chars in (300,2000,8000):
            v={**visit,'work_done':'Removed sediment; tested shower. '*(chars//35+1),
               'materials':'Replaced washers. '*50,'checks':'No visible drips observed. '*40,
               'unknowns':'Concealed source of deposits unknown. '*50}
            blob=card_pdf(card,[v]);pages=PdfReader(io.BytesIO(blob)).pages
            self.assertTrue(blob.startswith(b'%PDF-'));self.assertGreaterEqual(len(pages),2)
            full=' '.join(p.extract_text() or '' for p in pages)
            self.assertIn('HOW TO LOOK AFTER IT',full)
            self.assertIn('SERVICE IN BRIEF',full)
            self.assertIn('EUR 229.67',full)

    def test_very_long_care_advice_paginated(self):
        card,v=self.sample();plan=json.loads(v['care_plan'])
        plan['priority']='Monitor pressure, document water changes. '*75
        plan['routine_steps']=['Gently clean visible parts. '*120]*4
        v['care_plan']=json.dumps(plan)
        blob=card_pdf(card,[v]);r=PdfReader(io.BytesIO(blob))
        self.assertGreaterEqual(len(r.pages),2)
        self.assertIn('SERVICE IN BRIEF',' '.join(p.extract_text() or '' for p in r.pages))

    def test_short_chat_removes_bloated_citations(self):
        actual='**The problem:** Sediment blocked the shower pipe and lowered the water pressure. [Saved visit 2026-11-03]\n\nA worn seal caused dripping. [work_report.pdf]\n\nSources: work_report.pdf, invoice.pdf'
        result=short_chat_reply(actual)
        self.assertIn('Sediment blocked',result)
        self.assertNotIn('[Saved visit',result)
        self.assertNotIn('Sources:',result)
        self.assertNotIn('**',result)
        oversized='The shower had sediment buildup and a worn seal. '*100
        result=short_chat_reply(oversized,max_chars=220)
        self.assertLessEqual(len(result),222)

    def test_pdf_endpoint_with_large_saved_record(self):
        with tempfile.TemporaryDirectory(prefix='care_v6_') as tmp:
            port=freeport()
            env={**os.environ,'DATA_DIR':tmp,'PORT':str(port),'OPENAI_API_KEY':''}
            proc=subprocess.Popen([sys.executable,str(BASE/'server.py')],env=env,cwd=BASE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                x=Client(port)
                for _ in range(60):
                    try:
                        if x.call('/api/health')[0]==200:break
                    except Exception:time.sleep(.1)
                else: self.fail('server not started')
                x.call('/api/session')
                card,v=self.sample()
                fields={**card,**v,'work_done':'Heavy sediment. Replaced seal. '*125,
                    'findings':'Dirt in shower. '*175,'materials':'Seal set. '*100,
                    'checks':'Tested flow. '*180,'invoice_details':'EUR 229.67',
                    'care_plan':json.loads(v['care_plan']),'approved':True,'upload_ids':[]}
                status,created=x.call('/api/cards/create',fields)
                self.assertEqual(status,201,created)
                status,pdf=x.call('/api/cards/'+created['id']+'/pdf')
                self.assertEqual(status,200,pdf)
                self.assertTrue(pdf.startswith(b'%PDF-'))
                self.assertGreaterEqual(len(PdfReader(io.BytesIO(pdf)).pages),2)
            finally:
                proc.terminate();proc.wait(timeout=5)
                if proc.stderr:proc.stderr.close()

if __name__=='__main__':unittest.main()
