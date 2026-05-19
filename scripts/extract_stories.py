import json
data=json.load(open('fan-data-clean.json',encoding='utf-8'))
seen={}
for n in data['nodes']:
    if not n['interesting']: continue
    if n['story']: continue          # already has a story (original notables)
    if n['id'] in seen:
        if n['score']>seen[n['id']]['score']: seen[n['id']]=n
        continue
    seen[n['id']]=n
ppl=sorted(seen.values(),key=lambda x:-x['score'])
out=[]
for n in ppl:
    facts=[]
    for e in n['ev']:
        parts=[e['t'].replace('_',' ').title()]
        meta=' · '.join(x for x in [e['ti'],e['d'],e['pl']] if x)
        if meta: parts.append(meta)
        if e['desc']: parts.append(e['desc'])
        facts.append(': '.join(parts))
    out.append({'id':n['id'],'name':n['name'],'life':n['life'],
        'birth':n['bp'],'death':n['dp'],'origin':n['_country'] if False else '',
        'facts':facts,'sketch':n.get('sketch','')})
# country from bp
def country(p):
    if not p: return ''
    s=[x.strip() for x in p.split(',') if x.strip()]
    return s[-1] if s else ''
for o,n in zip(out,ppl):
    o['origin']=country(n['bp']) or country(n['dp'])
B=28
import math
nb=math.ceil(len(out)/B)
for i in range(nb):
    json.dump(out[i*B:(i+1)*B],open('story-batch-%d.json'%i,'w',encoding='utf-8'),ensure_ascii=False,indent=0)
print('notables needing stories:',len(out),'batches:',nb)
