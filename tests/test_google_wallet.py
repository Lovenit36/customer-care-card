import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import google_wallet

class WalletTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
        self.key_file=Path(self.temp.name)/'google-secret.json'
        self.key_file.write_text(json.dumps({
            'type':'service_account','client_email':'wallet-test@demo.iam.gserviceaccount.com',
            'private_key':private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode(),
            'token_uri':'https://oauth2.googleapis.com/token'}))
        self.env=patch.dict(os.environ,{
            'GOOGLE_WALLET_SERVICE_ACCOUNT_FILE':str(self.key_file),
            'GOOGLE_WALLET_ISSUER_ID':'1234567890',
            'PUBLIC_BASE_URL':'https://care.example.org'})
        self.env.start()
        self.card={'id':'f'*32,'business_name':'Test Plumber','product':'Shower pipe',
                   'trade':'Plumbing','service_date':'2026-11-02','maintenance_date':'',
                   'revoked':0,'customer_address':'Private Home','customer_phone':'0123456789',
                   'pin_hash':'RESTRICTED'}
        self.link='https://care.example.org/care/OPAQUE_TEST_TOKEN'
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_wallet_signing_and_api_flow(self):
        calls=[]
        def mock_api(access,method,path,payload=None):
            calls.append((method,path,payload))
            if method=='GET':return (404,{})
            return (200,{})
        with patch.object(google_wallet,'service_access_token',return_value='FAKE_API_ACCESS'),patch.object(google_wallet,'api_call',side_effect=mock_api):
            url=google_wallet.save_link(self.card,self.link)
        self.assertTrue(url.startswith('https://pay.google.com/gp/v/save/'))
        tok=url.rsplit('/',1)[1]
        obj=jwt.decode(tok,self.public,algorithms=['RS256'],audience='google')
        self.assertEqual(obj['payload']['genericObjects'][0]['id'],'1234567890.care_'+'f'*32)
        self.assertEqual(calls[1][0],'POST')
        self.assertEqual(calls[3][0],'POST')
        created=calls[3][2]
        self.assertIn('Shower pipe',str(created['textModulesData']))
        self.assertEqual(created['linksModuleData']['uris'][0]['uri'],self.link)
        self.assertNotIn('0123456789',str(created))
        self.assertNotIn('Private Home',str(created))
        self.assertNotIn('RESTRICTED',str(created))
    def test_existing_class_updates_existing_pass(self):
        calls=[]
        def mock_api(access,method,path,payload=None):
            calls.append(method)
            return (200,{})
        with patch.object(google_wallet,'service_access_token',return_value='FAKE_API_ACCESS'),patch.object(google_wallet,'api_call',side_effect=mock_api):
            google_wallet.save_link(self.card,self.link)
        self.assertEqual(calls,['GET','GET','PUT'])
    def test_not_configured_fails_explicitly(self):
        with patch.dict(os.environ,{'PUBLIC_BASE_URL':'http://localhost:8000'}):
            self.assertFalse(google_wallet.status()['enabled'])
            with self.assertRaises(google_wallet.WalletSetupError):google_wallet.save_link(self.card,'http://localhost:8000/care/TOKEN')
    def test_revoke_deactivates(self):
        obj=google_wallet.pass_object({**self.card,'revoked':1},self.link,'1234567890')
        self.assertEqual(obj['state'],'INACTIVE')

if __name__=='__main__':unittest.main()
