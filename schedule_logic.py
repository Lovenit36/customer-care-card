"""Validated appointment records and portable calendar downloads. No external services."""
import datetime as dt
import re

HEX_ID=re.compile(r'^[a-f0-9]{32}$')

def validate_appointment(value):
    if not isinstance(value,dict):raise ValueError('Appointment fields are missing.')
    title=str(value.get('title') or '').strip()
    if not 2<=len(title)<=120:raise ValueError('Appointment title must have 2–120 characters.')
    date=str(value.get('start_date') or '').strip()
    try:
        day=dt.date.fromisoformat(date)
        if day.isoformat()!=date:raise ValueError()
    except ValueError:raise ValueError('Choose a valid appointment date (YYYY-MM-DD).')
    time=str(value.get('start_time') or '').strip()
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',time):raise ValueError('Choose a valid start time (HH:MM).')
    duration=value.get('duration_minutes',60)
    if isinstance(duration,bool):raise ValueError('Invalid duration.')
    try:duration=int(duration)
    except (ValueError,TypeError):raise ValueError('Invalid duration.')
    if duration not in (15,30,45,60,90,120,180,240):raise ValueError('Choose a supported duration (15–240 minutes).')
    notes=str(value.get('notes') or '').strip()
    if len(notes)>2000:raise ValueError('Appointment notes must be 2,000 characters or fewer.')
    card_id=value.get('card_id') or None
    if card_id is not None and (not isinstance(card_id,str) or not HEX_ID.fullmatch(card_id)):
        raise ValueError('Invalid customer card reference.')
    return {'title':title,'start_date':date,'start_time':time,'duration_minutes':duration,'notes':notes,'card_id':card_id}

def esc(value):
    return str(value or '').replace('\\','\\\\').replace('\r','').replace('\n','\\n').replace(',','\\,').replace(';','\\;')

def ics_event(*, ident, title, date, hour, duration, description, alarm_minutes):
    start=dt.datetime.combine(dt.date.fromisoformat(date),dt.time.fromisoformat(hour))
    end=start+dt.timedelta(minutes=duration)
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return ['BEGIN:VEVENT','UID:'+esc(ident)+'@customer-care-card','DTSTAMP:'+stamp,
            'DTSTART:'+start.strftime('%Y%m%dT%H%M%S'),
            'DTEND:'+end.strftime('%Y%m%dT%H%M%S'),
            'SUMMARY:'+esc(title),'DESCRIPTION:'+esc(description),
            'BEGIN:VALARM','ACTION:DISPLAY','DESCRIPTION:'+esc(title),
            f'TRIGGER:-PT{alarm_minutes}M','END:VALARM','END:VEVENT']

def schedule_ics(data):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Customer Care Card//Appointment Calendar//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH']
    for a in data.get('appointments',[]):
        lines+=ics_event(ident='appointment-'+a['id'],title=a['title'],date=a['start_date'],hour=a['start_time'],
            duration=a['duration_minutes'],description=a.get('notes',''),alarm_minutes=30)
    for m in data.get('maintenance',[]):
        lines+=ics_event(ident='maintenance-'+m['card_id'],title='Maintenance: '+m['customer_name'],
            date=m['start_date'],hour='09:00',duration=30,description=m.get('maintenance_source',''),alarm_minutes=0)
    return ('\r\n'.join(lines+['END:VCALENDAR',''])).encode('utf-8')

def appointment_ics(appointment):
    return schedule_ics({'appointments':[appointment],'maintenance':[]})
