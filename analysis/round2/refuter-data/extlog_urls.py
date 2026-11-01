import json, sys, re, collections
EXTERNAL_LOG = re.compile(
    r"https?://(?:paste\.openstack\.org|pastebin\.com|gist\.github\.com|hastebin|dpaste|termbin|paste\.ubuntu\.com|bpa\.st"
    r"|logs\.openstack\.org|zuul\.opendev\.org|storage\.\S+?/zuul_opendev_logs|[^\s/]*\.?logs?\.[^\s/]+|gitlab\.com/[^\s]*/-/jobs/\d+"
    r"|drive\.google\.com|docs\.google\.com|dropbox\.com|wetransfer)\S*", re.I)
hosts = collections.Counter(); recs = 0; tot = 0
for line in open(sys.argv[1]):
    r = json.loads(line); tot += 1
    s = json.dumps(r, ensure_ascii=False)
    ms = EXTERNAL_LOG.findall(s)
    ms = [m.group(0) for m in EXTERNAL_LOG.finditer(s)]
    if ms: recs += 1
    for m in set(ms):
        hosts[re.sub(r"[0-9]+", "N", m)[:110]] += 1
print(tot, recs)
for h, c in hosts.most_common(12): print(c, h)
