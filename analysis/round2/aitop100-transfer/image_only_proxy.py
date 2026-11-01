import json, re, sys
IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img [^>]*>|https://user-images\.githubusercontent\S+|https://github\.com/user-attachments/assets/\S+|/uploads/[0-9a-f]+/[^)\s]+\.(?:png|jpe?g|gif)", re.I)
CODE = re.compile(r"```")
for fn, key in [(a.split(":")[0], a.split(":")[1]) for a in sys.argv[1:]]:
    n = img = short = nocode = 0
    for line in open(fn, encoding="utf-8"):
        n += 1; b = json.loads(line).get(key) or ""
        if not IMG.search(b): continue
        img += 1
        text = IMG.sub("", b)
        if len(text.strip()) < 400: short += 1
        if not CODE.search(text): nocode += 1
    print(fn.split("/")[-1], f"records={n} body_img={img} text_lt400={short} no_codeblock={nocode}")
