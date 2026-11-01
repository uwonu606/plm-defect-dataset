import sys, os, re, json
AVATAR = re.compile(r"https?://[^\"\s]*avatar[^\"\s]*", re.I)
pats = {
 "image": re.compile(r"!\[[^\]]*\]\(|\.(?:png|jpe?g|gif)\b|user-images\.githubusercontent|github\.com/user-attachments/assets", re.I),
 "pcap": re.compile(r"\.pcapng?\b|wireshark", re.I),
 "archive_or_logfile": re.compile(r"\.(?:zip|tar\.gz|tgz|gz|log)\b", re.I),
}
print("source\trecords\timage\tpcap\tarchive_or_logfile\tkeys_with_attach")
for path in sorted(sys.argv[1:]):
    n = 0; c = {k: 0 for k in pats}; attach_keys = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            n += 1
            line = AVATAR.sub("", line)
            for k, p in pats.items():
                if p.search(line): c[k] += 1
            if n <= 50:
                try: attach_keys |= {k for k in json.loads(line) if "attach" in k.lower()}
                except Exception: pass
    print(os.path.basename(path), n, *(f"{c[k]} ({c[k]/n:.1%})" for k in pats), ",".join(sorted(attach_keys)) or "-", sep="\t")
