import json,re
data=open('fan-data-clean.json',encoding='utf-8').read()
html=open('fan-chart.html',encoding='utf-8').read()
pat=re.compile(r'(<script id="data" type="application/json">).*?(</script>)',re.S)
new=pat.sub(lambda m:m.group(1)+data+m.group(2),html,count=1)
assert new!=html and len(new)>len(html)-10, 'no replacement'
open('fan-chart.html','w',encoding='utf-8').write(new)
print('embedded',len(data),'bytes; html now',len(new))
