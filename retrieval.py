"""Small, inspectable per-card retrieval. No external vector database or embeddings.

All sources are selected only after ownership checks in server.py. Chunk text
rather than treating an invoice as an instruction. Deterministic lexical retrieval
is enough for the small number of documents in this MVP.
"""
import math
import re
from collections import Counter

STOPWORDS = set('a an the and or to is are was were be been as at in on from for of by with it this that which what when how who me my you your can please tell about details information summarize summarise customer his her their show give data record'.split())

def words(text):
    return [w for w in re.findall(r'[\wäöüÄÖÜß€.-]+', (text or '').lower()) if len(w) > 2 and w not in STOPWORDS]

def chunks_from_sources(sources, size=1450, overlap=180):
    chunks=[]
    for source in sources:
        title=str(source['source'])[:160]
        txt=str(source.get('text') or '').strip()[:35000]
        if not txt:
            continue
        cursor=0
        while cursor<len(txt):
            end=min(len(txt),cursor+size)
            if end<len(txt):
                boundary=max(txt.rfind('\n',cursor+size//2,end),txt.rfind('. ',cursor+size//2,end))
                if boundary>cursor+size//2:end=boundary+1
            piece=txt[cursor:end].strip()
            if piece:chunks.append({'source':title,'text':piece})
            if end>=len(txt):break
            cursor=max(cursor+1,end-overlap)
    return chunks

def retrieve(sources, query, limit=9, max_chars=17000):
    """Rank independent document passages, preserving filename source labels."""
    chunks=chunks_from_sources(sources)
    if not chunks:return []
    q=Counter(words(query))
    docfreq=Counter()
    for item in chunks:docfreq.update(set(words(item['text'])))
    scores=[]
    for idx,item in enumerate(chunks):
        tokens=words(item['text']); c=Counter(tokens)
        score=0.0
        for term,count in q.items():
            if term not in c:continue
            idf=math.log(1+(len(chunks)-docfreq[term]+.5)/(docfreq[term]+.5))
            tf=c[term]*(2.2)/(c[term]+1.2*(.25+.75*len(tokens)/max(1,110)))
            score+=idf*tf
        # Earlier passages often define the job and have useful identifying context.
        scores.append((score, -idx, idx))
    scores.sort(reverse=True)
    selected=[]; total=0
    for score,_,idx in scores:
        item=chunks[idx]
        if score<=0 and selected and len(selected)>=min(3,limit):break
        if total+len(item['text'])>max_chars:continue
        selected.append(item);total+=len(item['text'])
        if len(selected)>=limit:break
    return selected

def format_evidence(chunks):
    return '\n\n'.join(f'[Source: {x["source"]}]\n{x["text"]}' for x in chunks)
