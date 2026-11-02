"""Pure, testable domain functions; do not infer product safety or warranty terms."""
import datetime as dt
import html
import re


def cleaned(v, max_len=4000):
    return str(v or '').strip()[:max_len]


def date_iso(v, *, allow_empty=True):
    if not v and allow_empty:
        return ''
    try:
        return dt.date.fromisoformat(v).isoformat()
    except (ValueError, TypeError):
        raise ValueError('Please enter a valid date (YYYY-MM-DD).')


def generate_due(service_date, interval_months):
    """Month-end stable when craftsman documents an interval."""
    if not service_date or not interval_months:
        return ''
    months = int(interval_months)
    if months < 1 or months > 120:
        raise ValueError('Maintenance interval must be 1–120 months.')
    src = dt.date.fromisoformat(service_date)
    index = src.year * 12 + src.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    if month == 12:
        nxt = dt.date(year + 1, 1, 1)
    else:
        nxt = dt.date(year, month + 1, 1)
    last = (nxt - dt.timedelta(days=1)).day
    return dt.date(year, month, min(src.day, last)).isoformat()


def determine_due_status(due, today=None):
    if not due:
        return 'not_set'
    today = today or dt.date.today()
    d = dt.date.fromisoformat(due)
    if d < today:
        return 'overdue'
    if d <= today + dt.timedelta(days=30):
        return 'soon'
    return 'upcoming'


def escape_pdf(v):
    return html.escape(cleaned(v, 10000)).replace('\n', '<br/>')


def redact_pii(text):
    """Best-effort minimisation; user must only upload data they may process."""
    t = cleaned(text, 25000)
    t = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', t)
    t = re.sub(r'(?<!\w)(?:\+\d{1,3}[ -]?)?(?:\d[\d ()-]{7,}\d)(?!\w)', '[PHONE/NUMBER]', t)
    return t


PLAN_FIELDS = ('priority','routine_steps','avoid','warning_signs','call_professional','schedule','basis')

def normalize_care_plan(value):
    """Only a reviewed aftercare plan is saved; text and lists are bounded."""
    import json
    if isinstance(value,str):
        try:value=json.loads(value) if value.strip() else {}
        except json.JSONDecodeError:raise ValueError('Invalid aftercare plan. Please review the plan and try again.')
    if not isinstance(value,dict):raise ValueError('Invalid aftercare plan.')
    result={}
    for k in PLAN_FIELDS:
        v=value.get(k,[] if k in ('routine_steps','avoid','warning_signs','call_professional') else '')
        if k in ('routine_steps','avoid','warning_signs','call_professional'):
            if isinstance(v,str):v=v.splitlines()
            if not isinstance(v,list):raise ValueError('Aftercare steps must be a list.')
            result[k]=[cleaned(x,400) for x in v[:12] if cleaned(x,400)]
        else:result[k]=cleaned(v,900)
    return result

def validate_care_input(data):
    required = ('business_name', 'business_contact', 'trade', 'customer_name', 'service_date', 'work_done')
    missing = [x.replace('_',' ') for x in required if not cleaned(data.get(x))]
    if missing:
        raise ValueError('Required: ' + ', '.join(missing))
    result = {key: cleaned(data.get(key), 6000 if key in ('work_done','problem','aftercare','summary','manual_evidence','findings','materials','checks','invoice_details','unknowns','source_references') else 400)
              for key in ('business_name','business_contact','trade','customer_name','customer_address','customer_phone',
                          'service_date','problem','work_done','product','manual_url','manual_evidence','aftercare','summary',
                          'maintenance_date','maintenance_source','warranty','warranty_source','findings','materials','checks','invoice_details','unknowns','source_references')}
    result['care_plan'] = normalize_care_plan(data.get('care_plan',{}))
    result['service_date'] = date_iso(result['service_date'], allow_empty=False)
    result['maintenance_date'] = date_iso(result['maintenance_date'])
    if result['manual_url'] and not result['manual_url'].startswith('https://'):
        raise ValueError('Manufacturer source link must start with https://')
    # No auto-invented due date. The craftsman must enter or approve it.
    if result['maintenance_date'] and not result['maintenance_source']:
        raise ValueError('Please specify the source of the maintenance date (e.g. technician or manual).')
    if result['warranty'] and not result['warranty_source']:
        raise ValueError('Please specify where the warranty information came from.')
    return result
