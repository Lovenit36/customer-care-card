"""Readable, offline customer aftercare PDF with concise service details and a calendar reminder."""
import io
import json
import html
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

INK=colors.HexColor('#122241')
BLUE=colors.HexColor('#115fcb')
SECONDARY=colors.HexColor('#526680')
FAINT=colors.HexColor('#f0f6ff')
PALE=colors.HexColor('#e5efff')
BORDER=colors.HexColor('#d7e4f4')

def esc(value):
    return html.escape(str(value or '')).replace('\n','<br/>')

def _plan(visit):
    val=visit.get('care_plan') or '{}'
    if isinstance(val,dict):return val
    try:return json.loads(val)
    except (ValueError,TypeError):return {}

def card_pdf(card, visits, url=None):
    """Aftercare first (roughly 60% of focus); essential work facts and history below."""
    output=io.BytesIO()
    doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=19*mm,leftMargin=19*mm,
        topMargin=15*mm,bottomMargin=15*mm,title='Customer Care Card - Aftercare Guide',author=card['business_name'])
    st=getSampleStyleSheet()
    st.add(ParagraphStyle(name='CareTop',fontName='Helvetica-Bold',fontSize=10,leading=13,textColor=BLUE,spaceAfter=5))
    st.add(ParagraphStyle(name='CareTitle',fontName='Helvetica-Bold',fontSize=21,leading=25,textColor=INK,spaceAfter=5))
    st.add(ParagraphStyle(name='CareBody',fontName='Helvetica',fontSize=10.2,leading=15.5,textColor=INK,spaceAfter=5))
    st.add(ParagraphStyle(name='CareSmall',fontName='Helvetica',fontSize=8.6,leading=12.5,textColor=SECONDARY,spaceAfter=4))
    st.add(ParagraphStyle(name='CareHeading',fontName='Helvetica-Bold',fontSize=12.6,leading=17,textColor=INK,spaceBefore=12,spaceAfter=6,keepWithNext=True))
    st.add(ParagraphStyle(name='CareMini',fontName='Helvetica-Bold',fontSize=9.5,leading=14,textColor=BLUE,spaceBefore=9,spaceAfter=3,keepWithNext=True))
    st.add(ParagraphStyle(name='CareBullet',parent=st['CareBody'],fontSize=9.4,leading=13.2,leftIndent=14,firstLineIndent=-11,spaceAfter=2))
    st.add(ParagraphStyle(name='CareDetailLabel',fontName='Helvetica-Bold',fontSize=8.3,leading=10.5,textColor=BLUE,spaceBefore=4,spaceAfter=0,keepWithNext=True))
    st.add(ParagraphStyle(name='CareDetailText',fontName='Helvetica',fontSize=8.3,leading=11.2,textColor=SECONDARY,spaceAfter=2))
    P=lambda x,style='CareBody':Paragraph(esc(x),st[style])
    latest=visits[0] if visits else {}
    plan=_plan(latest)
    routine=plan.get('routine_steps') or ([latest['aftercare']] if latest.get('aftercare') else [])
    story=[P('CUSTOMER CARE CARD  /  YOUR AFTERCARE GUIDE','CareTop'),
           P(card['customer_name'],'CareTitle'),
           P('Card reference: '+card['id'],'CareSmall'),
           P(str(card.get('product') or card.get('trade') or 'Service')+'  |  Latest recorded work: '+str(latest.get('service_date') or card.get('service_date') or ''),'CareSmall')]
    def section(name,content):
        if content:story.extend([P(name,'CareMini'),P(content)])
    def bullets(name,items,empty=None):
        items=[str(x).strip() for x in (items or []) if str(x).strip()]
        if not items and not empty:return
        story.append(P(name,'CareHeading'))
        if items:
            for i,text in enumerate(items,1):
                story.append(P(str(i)+'.  '+text,'CareBullet'))
        elif empty:story.append(P(empty,'CareSmall'))
    def mini_bullets(name,items):
        items=[str(x).strip() for x in (items or []) if str(x).strip()]
        if not items:return
        story.append(P(name,'CareMini'))
        for text in items:story.append(P('-  '+text,'CareBody'))

    priority=plan.get('priority') or 'Follow the reviewed advice provided by your craftsperson.'
    priority_table=Table([[P('MOST IMPORTANT','CareTop')],[P(priority)]],colWidths=[171*mm],hAlign='LEFT')
    priority_table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),FAINT),('LINEBEFORE',(0,0),(0,-1),3,BLUE),
        ('TOPPADDING',(0,0),(-1,0),8),('BOTTOMPADDING',(0,-1),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12)]))
    # A Table row cannot split across PDF pages. Use a normal paragraph when
    # unusually long priority notes would make the highlight box overfull.
    _, priority_height=priority_table.wrap(171*mm, 1000)
    if priority_height > 195:
        story.extend([Spacer(1,4*mm),P('MOST IMPORTANT','CareHeading'),P(priority)])
    else:
        story.extend([Spacer(1,4*mm),priority_table])
    # Side-by-side columns are deliberately 60% aftercare / 40% job facts.
    left=[P('HOW TO LOOK AFTER IT','CareHeading')]
    if routine:
        for i,step in enumerate(routine,1):left.append(P(str(i)+'.  '+step,'CareBullet'))
    else:left.append(P('No approved maintenance steps recorded. Ask your craftsperson.','CareSmall'))
    def side_list(target,title,values):
        values=[str(x).strip() for x in (values or []) if str(x).strip()]
        if not values:return
        target.append(P(title,'CareMini'))
        for s in values:target.append(P('-  '+s,'CareBody'))
    side_list(left,'Avoid',plan.get('avoid'))
    side_list(left,'Warning signs',plan.get('warning_signs'))
    side_list(left,'Contact your craftsperson when',plan.get('call_professional'))
    left.append(P('NEXT MAINTENANCE','CareMini'))
    left.append(P(card.get('maintenance_date') or plan.get('schedule') or 'No confirmed date yet'))
    if card.get('maintenance_source'):left.append(P('Source: '+card['maintenance_source'],'CareSmall'))
    if plan.get('basis'):left.append(P('Advice based on: '+plan['basis'],'CareSmall'))
    elif not latest.get('manual_evidence'):left.append(P('Manufacturer-specific instructions not verified.','CareSmall'))

    right=[P('SERVICE IN BRIEF - LATEST VISIT','CareHeading'),P('Date: '+str(latest.get('service_date') or 'Not recorded')+' | Customer: '+str(card.get('customer_name') or ''),'CareSmall')]
    def detail(title,value):
        if value:
            right.append(P(title,'CareDetailLabel'))
            right.append(P(value,'CareDetailText'))
    detail('Craft business',card.get('business_name'))
    detail('Contact',card.get('business_contact'))
    detail('Address',card.get('customer_address'))
    detail('Reported problem',latest.get('problem'))
    detail('Work done',latest.get('work_done') or latest.get('summary'))
    detail('Findings',latest.get('findings'))
    detail('Parts / checks',' / '.join(filter(None,[latest.get('materials'),latest.get('checks')])))
    detail('Invoice / cost',latest.get('invoice_details'))
    detail('Unknown / to verify',latest.get('unknowns'))
    detail('Warranty',latest.get('warranty'))
    detail('Sources',latest.get('source_references'))
    columns=Table([[left,right]],colWidths=[103*mm,68*mm],hAlign='LEFT')
    columns.setStyle(TableStyle([
       ('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(1,0),(1,0),FAINT),
       ('LEFTPADDING',(0,0),(0,0),0),('RIGHTPADDING',(0,0),(0,0),13),
       ('LEFTPADDING',(1,0),(1,0),10),('RIGHTPADDING',(1,0),(1,0),9),
       ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
    # A single table containing two *entire* columns cannot split tall rows.
    # It produced a LayoutError and HTTP 500 for realistic detailed records.
    # Keep the 60/40 side-by-side layout for short cards only. For longer cards,
    # lay out normal flowables so ReportLab can paginate them safely.
    _, columns_height=columns.wrap(171*mm, 10000)
    if columns_height <= 490 and priority_height <= 195:
        story.extend([Spacer(1,3*mm),columns])
    else:
        story.extend([Spacer(1,3*mm),*left,Spacer(1,3*mm),*right])
    if len(visits)>1:
        story.append(P('EARLIER WORK  /  PREVIOUS VISITS','CareHeading'))
        for v in visits[1:]:
            story.append(P((v.get('service_date') or 'Date unknown')+' | '+str(card.get('customer_name') or '')+' | '+(v.get('product') or 'Service'),'CareMini'))
            for label,key in (('Problem','problem'),('Work completed','work_done'),('Findings','findings'),('Materials','materials'),('Tests and inspections','checks'),('Invoice and cost','invoice_details'),('Previous aftercare','aftercare'),('Date for maintenance','maintenance_date')):
                val=v.get(key)
                if not val and key=='work_done':val=v.get('summary')
                if val:
                    story.extend([P(label,'CareDetailLabel'),P(val,'CareDetailText')])
    story.extend([Spacer(1,2*mm),P('Prepared from craftsperson-approved records. Keep this PDF on your phone for offline access. If information is missing, contact your craftsperson.','CareSmall')])
    doc.build(story)
    return output.getvalue()

def calendar_ics(card):
    """Portable calendar event with a standard alarm at 09:00 on the due date."""
    if not card['maintenance_date']:return b''
    import datetime
    from care_logic import cleaned
    escape=lambda v: cleaned(v,500).replace('\\','\\\\').replace('\n','\\n').replace(',','\\,').replace(';','\\;')
    date=card['maintenance_date'].replace('-','')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    parts=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Customer Care Card//EN','CALSCALE:GREGORIAN',
           'BEGIN:VEVENT','UID:care-'+card['id']+'@customer-care-card','DTSTAMP:'+stamp,
           'DTSTART:'+date+'T090000','DTEND:'+date+'T093000',
           'SUMMARY:'+escape('Customer maintenance: '+card['customer_name']),
           'DESCRIPTION:'+escape('Contact '+card['customer_name']+' for maintenance. '+card['business_name']),
           'BEGIN:VALARM','ACTION:DISPLAY','DESCRIPTION:Maintenance follow-up due today',
           'TRIGGER:-PT0M','END:VALARM','END:VEVENT','END:VCALENDAR','']
    return '\r\n'.join(parts).encode('utf-8')
