import json,collections
ev=json.loads(open('new-events.json',encoding='utf-8').read())
if isinstance(ev,str): ev=json.loads(ev)
data=json.load(open('fan-data-clean.json',encoding='utf-8'))
nodes=data['nodes']

WT={'NOBILITY_TITLE':5,'MILITARY_SERVICE':3,'IMMIGRATION':3,'OCCUPATION':2,'EDUCATION':2,
    'OTHER_FACT':2,'OTHER_EVENT':1.5,'RELIGIOUS_AFFILIATION':1,'CHRISTENING':0.5,
    'MARRIAGE':0.5,'RESIDENCE':0,'RACE':0}
def score(rec):
    s=0.0
    for e in rec['ev']:
        s+=WT.get(e['t'],1)
    s+=min(rec.get('mem',0),25)*1.0
    s+=min(rec.get('src',0),60)*0.25
    if rec.get('sketch'): s+=3
    return round(s,1)

DOMESTIC={'United States','British Colonial America','New France','New Netherland',
          'New Spain','North America',''}
def parseCountry(p):
    if not p: return ''
    seg=[x.strip() for x in p.split(',') if x.strip()]
    return seg[-1] if seg else ''

# score all new nodes
applied=0
scores=[]
for n in nodes:
    rec=ev.get(n['id'])
    if rec is None: continue
    n['ev']=rec['ev']
    n['mem']=rec.get('mem',n.get('mem',0))
    n['src']=rec.get('src',n.get('src',0))
    if rec.get('sketch'): n['sketch']=rec['sketch']
    sc=score(rec)
    n['score']=sc
    scores.append(sc)
    applied+=1

THRESH=7
ni=0
for n in nodes:
    if ev.get(n['id']) is not None:
        n['interesting']= n['score']>=THRESH
        if n['interesting']: ni+=1

# stats
import statistics
uniq={}
for n in nodes:
    if ev.get(n['id']) is not None:
        uniq[n['id']]=n
us=list(uniq.values())
intr=[n for n in us if n['interesting']]
amer=[n for n in intr if parseCountry(n['bp']) in DOMESTIC or parseCountry(n['dp']) in DOMESTIC and parseCountry(n['bp']) in DOMESTIC]
foreign=[n for n in intr if parseCountry(n['bp']) and parseCountry(n['bp']) not in DOMESTIC]
print('applied positions',applied,'unique new people',len(us))
print('new interesting (positions):',ni,' unique:',len(intr))
print('  foreign interesting:',len(foreign),' american-ish:',len(intr)-len(foreign))
print('score pctiles:',[round(statistics.quantiles(scores,n=10)[i],1) for i in range(9)])
data['meta']['nodes']=len(nodes)
json.dump(data,open('fan-data-clean.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print('saved')
