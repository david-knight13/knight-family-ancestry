"""Embed data/fan-data-clean.json into index.html."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
data = (PROJ / "data" / "fan-data-clean.json").read_text(encoding="utf-8")
html_path = PROJ / "index.html"
html = html_path.read_text(encoding="utf-8")
pat = re.compile(r'(<script id="data" type="application/json">).*?(</script>)', re.S)
new, n = pat.subn(lambda m: m.group(1) + data + m.group(2), html, count=1)
assert n == 1 and new != html, "no replacement"
html_path.write_text(new, encoding="utf-8")
print("embedded", len(data), "bytes; html now", len(new))
