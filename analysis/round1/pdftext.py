import re,sys,zlib
data=open(sys.argv[1],'rb').read()
out=[]
for m in re.finditer(rb'stream\r?\n(.*?)\r?\nendstream',data,re.S):
    try: s=zlib.decompress(m.group(1))
    except Exception: continue
    if b'BT' not in s: continue
    parts=[]
    for tj in re.finditer(rb'\[(.*?)\]\s*TJ|\((.*?)(?<!\\)\)\s*Tj',s,re.S):
        if tj.group(1) is not None:
            parts.append(b''.join(re.findall(rb'\((.*?)(?<!\\)\)',tj.group(1),re.S)))
        else: parts.append(tj.group(2))
        parts.append(b' ')
    out.append(b''.join(parts))
txt=b'\n'.join(out).decode('latin-1')
print(txt)
