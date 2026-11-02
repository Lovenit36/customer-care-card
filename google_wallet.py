"""Google Wallet Generic pass integration.

Requires a Google Wallet issuer ID, authorized service account JSON, and a real HTTPS
PUBLIC_BASE_URL. Never put passwords/PINs or full job history in Google Wallet.
The pass contains a short service reference, approved service dates and an authenticated
URL. The detailed customer record is still protected by the application's six-digit PIN.
"""
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import jwt

API='https://walletobjects.googleapis.com/walletobjects/v1'
SCOPES=['https://www.googleapis.com/auth/wallet_object.issuer']

class WalletSetupError(ValueError): pass
class WalletProviderError(RuntimeError): pass


def status():
    base=os.getenv('PUBLIC_BASE_URL','').rstrip('/')
    issuer=os.getenv('GOOGLE_WALLET_ISSUER_ID','').strip()
    path=os.getenv('GOOGLE_WALLET_SERVICE_ACCOUNT_FILE','').strip()
    if not base.startswith('https://'):
        return {'enabled':False,'reason':'Google Wallet needs a publicly accessible HTTPS PUBLIC_BASE_URL (localhost cannot work).'}
    if not re.fullmatch(r'\d+',issuer):
        return {'enabled':False,'reason':'Set GOOGLE_WALLET_ISSUER_ID from Google Pay & Wallet Console.'}
    if not path or not Path(path).expanduser().is_file():
        return {'enabled':False,'reason':'Set GOOGLE_WALLET_SERVICE_ACCOUNT_FILE to your private Google service account JSON file.'}
    return {'enabled':True,'reason':'Issuer configured. Wallet availability still depends on Google approval and credentials.'}


def localized(value):
    return {'defaultValue': {'language':'en-US','value':str(value)[:120]}}


def credentials():
    setting=status()
    if not setting['enabled']:raise WalletSetupError(setting['reason'])
    path=Path(os.getenv('GOOGLE_WALLET_SERVICE_ACCOUNT_FILE')).expanduser()
    try:
        raw=json.loads(path.read_text(encoding='utf-8'))
        if raw.get('type')!='service_account' or not raw.get('client_email') or not raw.get('private_key'):
            raise WalletSetupError('Google service account JSON is missing required signing credentials.')
        return raw
    except (OSError,ValueError) as e:
        raise WalletSetupError('Could not open Google service account JSON. Check its path and permissions.') from e


def service_access_token(raw):
    """OAuth2 JWT bearer assertion for Google Wallet REST API (RFC 7523)."""
    issued=int(time.time())
    token_url=raw.get('token_uri','https://oauth2.googleapis.com/token')
    claims={'iss':raw['client_email'],'scope':SCOPES[0],'aud':token_url,'iat':issued,'exp':issued+3600}
    assertion=jwt.encode(claims,raw['private_key'],algorithm='RS256')
    body=urlencode({'grant_type':'urn:ietf:params:oauth:grant-type:jwt-bearer','assertion':assertion}).encode()
    try:
        with urlopen(Request(token_url,data=body,headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST'),timeout=20) as r:
            return json.loads(r.read())['access_token']
    except Exception as e:
        raise WalletProviderError('Google service account authentication failed. Check API enablement and credentials.') from e


def api_call(access_token, method, path, payload=None):
    body=None if payload is None else json.dumps(payload).encode()
    req=Request(API+path,data=body,method=method,headers={
        'Authorization':'Bearer '+access_token,'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=20) as r:
            return r.status, json.loads(r.read() or b'{}')
    except HTTPError as e:
        return e.code, {}
    except Exception as e:
        raise WalletProviderError('Google Wallet API could not be reached.') from e


def require_success(result,where):
    code,_=result
    if code not in (200,201,204):
        raise WalletProviderError('Google Wallet '+where+' rejected the pass (HTTP '+str(code)+'). Check issuer permissions and approval.')

def pass_object(card, public_url, issuer):
    # Deterministic ID allows the REST API to update the same pass when work is updated.
    # Personal address, phone, PIN and full job details intentionally stay on PIN-locked page.
    obj={
        'id':issuer+'.care_'+card['id'],
        'classId':issuer+'.customer_care_cards',
        'state':'INACTIVE' if card['revoked'] else 'ACTIVE',
        'cardTitle':localized('Customer Care Card'),
        'header':localized(card['business_name'] or 'Service record'),
        'subheader':localized('Service card · '+card['id'][:8].upper()),
        'hexBackgroundColor':'#1B64C8',
        'barcode':{'type':'QR_CODE','value':public_url,'alternateText':'Open secure service record'},
        'textModulesData':[
            {'id':'service','header':'Service','body':str(card['product'] or card['trade'] or 'Completed service')[:160]},
            {'id':'serviced','header':'Last service','body':str(card['service_date'] or 'Not recorded')},
            {'id':'maintenance','header':'Next maintenance','body':str(card['maintenance_date'] or 'Not recorded')},
        ],
        'linksModuleData':{'uris':[{'id':'open_record','uri':public_url,'description':'Open full care history (PIN required)'}]}
    }
    return obj


def save_link(card,public_url):
    raw=credentials()
    issuer=os.getenv('GOOGLE_WALLET_ISSUER_ID').strip()
    if not public_url.startswith('https://'):
        raise WalletSetupError('Customer service link must be public HTTPS for Google Wallet.')
    access=service_access_token(raw)
    class_id=issuer+'.customer_care_cards'
    class_path='/genericClass/'+quote(class_id,safe='')
    code,_=api_call(access,'GET',class_path)
    if code==404:
        require_success(api_call(access,'POST','/genericClass',{'id':class_id}),'class creation')
    elif code!=200:
        raise WalletProviderError('Google Wallet class lookup failed (HTTP '+str(code)+').')
    obj=pass_object(card,public_url,issuer)
    obj_path='/genericObject/'+quote(obj['id'],safe='')
    code,_=api_call(access,'GET',obj_path)
    if code==404:
        require_success(api_call(access,'POST','/genericObject',obj),'object creation')
    elif code==200:
        require_success(api_call(access,'PUT',obj_path,obj),'object update')
    else:
        raise WalletProviderError('Google Wallet object lookup failed (HTTP '+str(code)+').')
    claims={'iss':raw['client_email'],'aud':'google','typ':'savetowallet','iat':int(time.time()),
            'origins':[os.getenv('PUBLIC_BASE_URL').rstrip('/')],
            'payload':{'genericObjects':[{'id':obj['id']}]}}
    signed=jwt.encode(claims,raw['private_key'],algorithm='RS256')
    return 'https://pay.google.com/gp/v/save/'+signed


def update_if_configured(card, public_url):
    """Best-effort sync on update/rotation/revoke; never block local data updates."""
    if not status()['enabled']:return False
    try:
        raw=credentials();issuer=os.getenv('GOOGLE_WALLET_ISSUER_ID').strip()
        access=service_access_token(raw)
        obj=pass_object(card,public_url,issuer)
        path='/genericObject/'+quote(obj['id'],safe='')
        code,_=api_call(access,'GET',path)
        if code!=200:return False  # Never create a pass without user action
        require_success(api_call(access,'PUT',path,obj),'pass update')
        return True
    except Exception:
        return False
