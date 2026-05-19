import json,glob
stories={}
for f in sorted(glob.glob('story-out-*.json')):
    try:
        d=json.load(open(f,encoding='utf-8'))
        stories.update(d)
    except Exception as e:
        print('skip',f,e)
data=json.load(open('fan-data-clean.json',encoding='utf-8'))
applied=0
for n in data['nodes']:
    if not n['story'] and n['id'] in stories:
        n['story']=stories[n['id']]
        applied+=1
json.dump(data,open('fan-data-clean.json','w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print('stories collected:',len(stories),'applied to node-positions:',applied)
