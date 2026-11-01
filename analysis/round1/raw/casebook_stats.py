import json, re, sys
from collections import Counter
d=json.load(open(sys.argv[1]))
inc=[c for r,c in d["一覧（事故）"][1:]]
print("incident rows", len(inc), "distinct No", len({c.get('A') for c in inc}))
print("missing No rows", sum(1 for c in inc if 'A' not in c))
print("year", Counter(re.sub(r"[ァ-ヶー]+","",c.get("B","")) for c in inc).most_common())
print("発生要因", Counter(re.sub(r"[ァ-ヶー]+$","",c.get("L","")) for c in inc).most_common())
print("重大事故該当", Counter(c.get("I","")[:1] for c in inc))
print("事業者 top", Counter(re.sub(r"[ァ-ヶー]+$","",c.get("C","")) for c in inc).most_common(10))
kw={"ソフトウェア/バグ":r"ソフトウェア|バグ|不具合|プログラム","ファームウェア":r"ファームウェア","ベンダー":r"ベンダ","設定/作業ミス":r"設定|作業ミス|誤","輻輳/高負荷":r"輻輳|高負荷|負荷","冗長/切替失敗":r"冗長|切替|切り替","移動体/基地局/コア":r"基地局|携帯|LTE|５Ｇ|5G|4G|コア|HSS|MME|加入者|VoLTE|IMS|パケット交換","クラウド/仮想化":r"仮想|クラウド","証明書/期限":r"証明書|期限","電源/停電/災害":r"電源|停電|地震|台風|火災"}
for k,p in kw.items():
    print(f"  M(原因) contains {k}: {sum(1 for c in inc if re.search(p, c.get('M','')))}")
les=[c for r,c in d["一覧（教訓）"][2:]]
print("lesson rows", len(les))
print("段階", Counter(re.sub(r"[ァ-ヶー]+$","",c.get("C","")) for c in les).most_common())
heads=Counter(re.match(r"【([^】]+)】", c.get("D","") or "").group(1) if re.match(r"【([^】]+)】", c.get("D","") or "") else "?" for c in les)
print("教訓 heading distinct", len(heads), heads.most_common(12))
print("lessons referencing incident No?", sum(1 for c in les if re.search(r"No\.?\s*\d+|事故\d+", c.get("E",""))))
print("lessons marked 新規事例", sum(1 for c in les if "新規事例" in c.get("E","")))
