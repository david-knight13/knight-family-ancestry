import json
raw=open('new-ancestors.json',encoding='utf-8').read()
d=json.loads(raw)
if isinstance(d,str): d=json.loads(d)

CHAIN=['Florida','Georgia','Alabama','Mississippi','Louisiana','Texas','Arkansas',
 'Missouri','Illinois','Kentucky','Tennessee','South Carolina','North Carolina','Virginia',
 'Maryland','Delaware','Pennsylvania','New Jersey','New York','Connecticut','Rhode Island',
 'Massachusetts','New Hampshire','Maine','Acadia','Nova Scotia','Oregon']

def states_of(place):
    if not place: return []
    found=[]
    for seg in [s.strip() for s in place.split(',')]:
        for st in CHAIN:
            if st in seg and st not in found:
                found.append(st)
    return found

ex=json.load(open('fan-data-clean.json',encoding='utf-8'))
exnodes=ex['nodes']
existing_gp=set((n['gen'],n['pos']) for n in exnodes)

merged=list(exnodes)
collisions=0; added=0
for n in d:
    gp=(n['gen'],n['pos'])
    if gp in existing_gp:
        collisions+=1; continue
    existing_gp.add(gp)
    st=states_of(n['bp'])
    for s in states_of(n['dp']):
        if s not in st: st.append(s)
    primary=st[0] if st else 'Unknown'
    merged.append({
      'pos':n['pos'],'gen':n['gen'],'id':n['id'],'name':n['name'],'life':n['life'],
      'bp':n['bp'],'dp':n['dp'],'states':st,'primary':primary,
      'score':0,'interesting':False,'ev':[],'sketch':'','mem':n['mem'],'src':n['src'],'story':''})
    added+=1

ex['nodes']=merged
ex['meta']['nodes']=len(merged)
ex['meta']['maxGen']=max(n['gen'] for n in merged)
ex['meta']['crawlExtended']=added
json.dump(ex,open('fan-data-clean.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print('added',added,'collisions',collisions,'total',len(merged),'maxGen',ex['meta']['maxGen'])
