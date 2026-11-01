import zipfile, re, sys, json
import xml.etree.ElementTree as ET
NS={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main","r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
z=zipfile.ZipFile(sys.argv[1])
print([i.filename for i in z.infolist()])
ss=[]
if "xl/sharedStrings.xml" in z.namelist():
    for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si",NS):
        ss.append("".join(t.text or "" for t in si.iter("{%s}t"%NS["m"])))
wb=ET.fromstring(z.read("xl/workbook.xml"))
rels=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
rmap={r.get("Id"):r.get("Target") for r in rels}
def col(ref): return re.match(r"[A-Z]+",ref).group()
out={}
for sh in wb.find("m:sheets",NS):
    target=rmap[sh.get("{%s}id"%NS["r"])]
    xml=ET.fromstring(z.read("xl/"+target.lstrip("/").replace("xl/","")))
    rows=[]
    for row in xml.iter("{%s}row"%NS["m"]):
        cells={}
        for c in row.findall("m:c",NS):
            v=c.find("m:v",NS); t=c.get("t")
            if t=="s" and v is not None: val=ss[int(v.text)]
            elif t=="inlineStr": val="".join(x.text or "" for x in c.iter("{%s}t"%NS["m"]))
            else: val=v.text if v is not None else None
            if val not in (None,""): cells[col(c.get("r"))]=val
        if cells: rows.append((row.get("r"),cells))
    out[sh.get("name")]=rows
    print(f"== sheet {sh.get('name')} rows-with-data {len(rows)}")
json.dump(out, open(sys.argv[2],"w",encoding="utf-8"), ensure_ascii=False)
