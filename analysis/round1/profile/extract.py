import json
import re
from collections import defaultdict

DATASET = "./dataset"
TEXT_FIELDS = ["title", "location", "problem", "cause", "resolution"]


def load(name):
    with open(f"{DATASET}/{name}.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def record_text(rec, fields=TEXT_FIELDS):
    return "\n".join(rec.get(f) or "" for f in fields)


def repo_of(source_id):
    return source_id.split("#")[0]


def bounded(alias):
    return r"(?<![A-Za-z0-9_])" + alias + r"(?![A-Za-z0-9_])"


NF_ALIASES = {
    "AMF": [r"AMF"], "SMF": [r"SMF"], "UPF": [r"UPF"], "NRF": [r"NRF"],
    "AUSF": [r"AUSF"], "UDM": [r"UDM"], "UDR": [r"UDR"], "PCF": [r"PCF"],
    "NSSF": [r"NSSF"], "NEF": [r"NEF"], "BSF": [r"BSF"], "SCP": [r"SCP"],
    "SEPP": [r"SEPP"], "N3IWF": [r"N3IWF"], "SMSF": [r"SMSF"], "CHF": [r"CHF"],
    "MME": [r"MME"], "SGW": [r"SGW(?:-[CU])?", r"S-GW", r"SGWC", r"SGWU"],
    "PGW": [r"PGW(?:-[CU])?", r"P-GW", r"PGWC", r"PGWU"], "SPGW": [r"SPGW(?:-[CU])?"],
    "HSS": [r"HSS"], "PCRF": [r"PCRF"],
    "gNB": [r"gNB", r"gNodeB"], "eNB": [r"eNB", r"eNodeB"], "ng-eNB": [r"ng-eNB"],
    "CU": [r"CU", r"CU-CP", r"CU-UP", r"gNB-CU"], "DU": [r"DU", r"gNB-DU"],
    "UE": [r"UE", r"nrUE", r"lteUE"], "RU": [r"RU", r"O-RU"], "RIC": [r"RIC", r"Near-RT RIC", r"nearRT-RIC"],
    "EPC": [r"EPC"], "5GC": [r"5GC"],
}

IFACE_ALIASES = {
    "NGAP": [r"NGAP"], "F1AP": [r"F1AP"], "E1AP": [r"E1AP"], "S1AP": [r"S1AP"],
    "X2AP": [r"X2AP"], "XnAP": [r"XnAP"], "E2AP": [r"E2AP"], "PFCP": [r"PFCP"],
    "GTP-U": [r"GTP-U", r"GTPv1-U", r"GTPU"], "GTP-C": [r"GTP-C", r"GTPv2(?:-C)?", r"GTPv2C"],
    "GTP": [r"GTP"], "SCTP": [r"SCTP"],
    "NAS": [r"NAS", r"NAS-5GS", r"5GMM", r"5GSM", r"EMM", r"ESM"],
    "RRC": [r"RRC"], "PDCP": [r"PDCP"], "RLC": [r"RLC"], "MAC": [r"MAC(?!\s*(?:address|주소|addr))"],
    "PHY": [r"PHY"], "SDAP": [r"SDAP"], "Diameter": [r"Diameter"], "S6a": [r"S6a"], "Gx": [r"Gx"],
    "SBI": [r"SBI"], "HTTP/2": [r"HTTP/2", r"HTTP2"], "FAPI": [r"n?FAPI"], "eCPRI": [r"eCPRI"],
    "fronthaul": [r"fronthaul", r"OFH"], "NETCONF": [r"NETCONF"], "YANG": [r"YANG"],
    "ASN.1": [r"ASN\.1"],
    "N1": [r"N1"], "N2": [r"N2"], "N3": [r"N3"], "N4": [r"N4"], "N6": [r"N6"], "N9": [r"N9"],
    "S1-U": [r"S1-U"], "S1-MME": [r"S1-MME"], "S1": [r"S1"], "S5": [r"S5"], "S8": [r"S8"],
    "S11": [r"S11"], "F1": [r"F1(?:-[CU])?"], "E1": [r"E1"], "Xn": [r"Xn"], "X2": [r"X2"],
    "Uu": [r"Uu"], "E2": [r"E2"], "O1": [r"O1"], "A1": [r"A1"],
}

NEUTRON_ALIASES = {
    "OVS": [r"OVS", r"Open vSwitch", r"openvswitch"], "OVN": [r"OVN"], "ML2": [r"ML2"],
    "L3 agent": [r"L3 agent", r"l3[-_]agent"], "DHCP agent": [r"DHCP agent", r"dhcp[-_]agent"],
    "metadata agent": [r"metadata agent", r"metadata[-_]agent"], "LinuxBridge": [r"[Ll]inux ?[Bb]ridge"],
    "SR-IOV": [r"SR-IOV", r"SRIOV"], "VXLAN": [r"VXLAN"], "GRE": [r"GRE"], "VLAN": [r"VLAN"],
    "iptables": [r"iptables"], "conntrack": [r"conntrack"], "security group": [r"security group", r"security_group", r"\bSG\b"],
    "floating IP": [r"floating IP", r"floatingip", r"FIP"], "router": [r"router"],
    "DVR": [r"DVR"], "HA router": [r"HA router", r"L3 HA"], "keepalived": [r"keepalived"],
    "dnsmasq": [r"dnsmasq"], "haproxy": [r"haproxy"], "port binding": [r"port binding", r"binding:\w+"],
    "QoS": [r"QoS"], "trunk": [r"trunk"], "BGP": [r"BGP"], "DPDK": [r"DPDK"],
}


def compile_dict(aliases):
    return {canon: re.compile("|".join(bounded(a) for a in pats)) for canon, pats in aliases.items()}


NF_RE = compile_dict(NF_ALIASES)
IFACE_RE = compile_dict(IFACE_ALIASES)
NEUTRON_RE = compile_dict(NEUTRON_ALIASES)

SBI_SERVICE_RE = re.compile(r"(?<![A-Za-z])(N(?:amf|smf|nrf|ausf|udm|udr|pcf|nssf|nef|bsf|smsf|chf|upf)_[A-Z][A-Za-z]+)")
SBI_PATH_RE = re.compile(r"/(n(?:amf|smf|nrf|ausf|udm|udr|pcf|nssf|nef|bsf|smsf|chf)-[a-z-]+)/v\d")

SPEC_RE = re.compile(r"(?:TS|TR)\s?(\d{2}\.\d{3})(?:[^\n]{0,25}?(?:§|clause|section|절|sec\.?|Sec\.?)?\s*(\d+(?:\.\d+){1,4}))?")
SPEC_BARE_RE = re.compile(r"(?<![\d.])(2[2-9]\.\d{3}|3[3-8]\.\d{3})(?![\d.])")
ORAN_RE = re.compile(r"O-RAN[ .]WG\d+[\w.-]*|O-RAN\.WG\d")
RFC_RE = re.compile(r"RFC ?(\d{3,5})")

CODE_EXT = r"(?:c|cc|cpp|cxx|h|hh|hpp|go|py|rs|java|js|ts|sh|cmake|yaml|yml|conf|cfg|json|ini|xml|j2|proto|asn1?|txt|toml|mk)"
FILE_RE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w-]+(?:\.[\w-]+)*\." + CODE_EXT + r")(?::\d+)?(?![\w])")
FUNC_RE = re.compile(r"(?<![\w.])([A-Za-z_][\w]*(?:(?:::|\.|->)[A-Za-z_]\w*)*)\s*\((?:\)|[^()`]{0,60}\))")
FUNC_STOPWORDS = {"if", "for", "while", "switch", "return", "sizeof", "printf", "assert", "AssertionError", "e.g", "i.e",
                  "PR", "MR", "commit", "review", "bug", "issue", "TS", "Rel", "v", "LOG_D", "LOG_E", "LOG_I", "LOG_W"}
BARE_CALL_RE = re.compile(r"(?<![\w.])([A-Za-z_][\w]*(?:(?:::|\.|->)[A-Za-z_]\w*)*)\(\)")
BACKTICK_RE = re.compile(r"`([^`\n]{1,200})`")
IDENT_RE = re.compile(r"^[A-Za-z_][\w.-]*$")
CONFIG_CONTEXT_RE = re.compile(r"설정|config|conf\b|\.conf|yaml|yml|옵션|option|파라미터|parameter|cfg|\.ini|flag|knob|키", re.I)
ASSIGN_RE = re.compile(r"^([A-Za-z_][\w.\-\[\]]*)\s*[:=]\s*\S")

VERSION_RE = re.compile(
    r"(?<![\w.])(v\d+\.\d+(?:\.\d+){0,2}(?:-rc\d+)?|\d+\.\d+\.\d+(?:-rc\d+)?(?!\.\d)|20\d\d\.w\d\d|Rel-?\d{2}(?:\.\d+)?|Release ?\d{2}"
    r"|(?:Folsom|Grizzly|Havana|Icehouse|Juno|Kilo|Liberty|Mitaka|Newton|Ocata|Pike|Queens|Rocky|Stein|Train|Ussuri|Victoria|Wallaby|Xena|Yoga|Zed|Antelope|Bobcat|Caracal|Dalmatian|Epoxy|Flamingo)"
    r"|stable/[a-z0-9.]+|RHOSP ?\d+(?:\.\d+)?|OSP ?\d+)(?![\w])")

EXC_RE = re.compile(r"(?<![\w.])([A-Z][A-Za-z0-9]*(?:Error|Exception|Fault|Failure|Timeout))(?![\w])")
SIGNAL_RE = re.compile(r"SIGSEGV|SIGABRT|SIGBUS|SIGFPE|SIGILL|SIGKILL|SIGPIPE|segfault|[Ss]egmentation fault|core dump(?:ed)?|double free|heap-use-after-free|stack-buffer-overflow|heap-buffer-overflow|use-after-free")
ASSERT_RE = re.compile(r"[Aa]ssert(?:ion)?\s*(?:failed)?[:\s]*[`'\"(]+([^`'\"\n]{3,160}?)[`'\")]+\s*(?:failed|실패)?|AssertionError:?\s*([^`\n]{3,120})|DevAssert\(([^)]{3,120})\)|AssertFatal\(([^,]{3,120}),")
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
PANIC_RE = re.compile(r"panic: ([^`\n]{3,120})")
LOGLINE_RE = re.compile(r"`([^`\n]*(?:\[ERRO\]|ERROR|FATAL|CRITICAL|\[error\]|\[fatal\]|failed|Failed|ERR\b|Traceback)[^`\n]*)`")

ISSUE_REF_RE = re.compile(r"(?:(PR|MR|issue|Issue|bug|Bug|버그|이슈)\s*)?(#|!|bug\s)(\d{1,7})")
LP_BUG_RE = re.compile(r"(?:bug|Bug|버그|LP|lp)[ #:]*(\d{5,7})|(?<![\d])#(\d{6,7})(?!\d)|bugs\.launchpad\.net/(?:\w+/\+bug|bugs)/(\d{5,7})")
COMMIT_RE = re.compile(r"(?<![\w/])([0-9a-f]{7,40})(?![\w])")
REVIEW_RE = re.compile(r"(?:review|Change|change)\s*(\d{4,6})|review\.(?:opendev|openstack)\.org/(?:#/c/)?(\d{4,6})")
URL_REF_RE = re.compile(r"(?:github\.com|gitlab\.[\w.]+)/([\w.-]+/[\w.-]+)/(?:-/)?(issues|pull|merge_requests)/(\d+)")

BACKTRACE_FRAME_RE = re.compile(r"\s+(?:0x[0-9a-f]+|in\s|at\s|[A-Za-z_]\w*\s*\()")
NON_ISSUE_PRECEDERS = re.compile(r"(?:cause|Cause|frame|Frame|thread|Thread|core|Core|gNB|UE|eNB|cell|Cell|slot|port|step|Step|test|단계|PDU|QFI|DRB|SRB|PDR|FAR|URR|QER|item|Item|No\.|번)\s*$")


def normalize_signature(text):
    text = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", text)
    text = re.sub(r"\b[0-9a-f]{8,}\b", "<HEX>", text)
    text = re.sub(r"\d+\.\d+\.\d+\.\d+(?::\d+)?", "<IP>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*", "<TS>", text)
    text = re.sub(r"\d+", "<N>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_commit_hash(token):
    return bool(re.search(r"[a-f]", token)) and bool(re.search(r"\d", token)) and not token.isdigit()


def extract_dict(text, compiled):
    found = set()
    for canon, rx in compiled.items():
        if rx.search(text):
            found.add(canon)
    return found


def extract_specs(text):
    specs = set()
    clauses = set()
    for m in SPEC_RE.finditer(text):
        specs.add("TS " + m.group(1))
        if m.group(2):
            clauses.add(f"TS {m.group(1)} §{m.group(2)}")
    for m in ORAN_RE.finditer(text):
        specs.add(m.group(0))
    for m in RFC_RE.finditer(text):
        specs.add("RFC " + m.group(1))
    return specs, clauses


def extract_code(text):
    funcs, files = set(), set()
    for m in FILE_RE.finditer(text):
        path = m.group(1)
        if re.fullmatch(r"v?\d+(?:\.\d+)+\.\w+", path):
            continue
        files.add(path.rsplit("/", 1)[-1])
    candidates = [m.group(1) for m in BARE_CALL_RE.finditer(text)]
    for bt in BACKTICK_RE.finditer(text):
        candidates += [m.group(1) for m in FUNC_RE.finditer(bt.group(1))]
    for name in candidates:
        if name in FUNC_STOPWORDS or len(name) < 3:
            continue
        if not ("_" in name or re.search(r"[a-z][A-Z]", name) or "::" in name or "->" in name or "." in name):
            continue
        funcs.add(name.split("->")[-1].split("::")[-1].split(".")[-1])
    return funcs, files


def extract_config_keys(text):
    keys = set()
    for m in BACKTICK_RE.finditer(text):
        tok = m.group(1).strip()
        am = ASSIGN_RE.match(tok)
        if am and FILE_RE.fullmatch(am.group(1)):
            continue
        if am and ("_" in am.group(1) or "." in am.group(1) or "-" in am.group(1)):
            keys.add(am.group(1))
            continue
        if not IDENT_RE.match(tok) or FILE_RE.fullmatch(tok) or EXC_RE.search(tok):
            continue
        if not ("_" in tok or "." in tok or "-" in tok):
            continue
        window = text[max(0, m.start() - 40): m.end() + 40]
        if CONFIG_CONTEXT_RE.search(window):
            keys.add(tok)
    return keys


def extract_versions(text):
    return {m.group(1) for m in VERSION_RE.finditer(text)}


def extract_errors(text):
    generic, specific = set(), set()
    for m in EXC_RE.finditer(text):
        if m.group(1) not in {"Error", "Exception"}:
            generic.add("exc:" + m.group(1))
    for m in SIGNAL_RE.finditer(text):
        generic.add("sig:" + m.group(0).lower().replace("segmentation fault", "segfault").replace("core dumped", "core dump"))
    for m in ASSERT_RE.finditer(text):
        expr = next(g for g in m.groups() if g)
        if HANGUL_RE.search(expr) or not re.search(r"[A-Za-z_]{2}", expr):
            continue
        sig = normalize_signature(expr)
        target = specific if len(re.findall(r"[A-Za-z_]", sig.replace("<N>", ""))) >= 4 else generic
        target.add("assert:" + sig)
    for m in PANIC_RE.finditer(text):
        specific.add("panic:" + normalize_signature(m.group(1)))
    for m in LOGLINE_RE.finditer(text):
        sig = normalize_signature(m.group(1))
        if re.fullmatch(r"Assertion \(<N>\) failed!?", sig):
            generic.add("assert:" + sig)
        elif len(sig) >= 12:
            specific.add("log:" + sig)
    return generic, specific


def extract_refs(text, source_id):
    repo = repo_of(source_id)
    issue_refs, mr_refs, commits, reviews, lp_bugs = set(), set(), set(), set(), set()
    is_gitlab = repo.startswith(("oai/", "ocudu/", "duranta-project/"))
    if repo.startswith("launchpad:"):
        for m in LP_BUG_RE.finditer(text):
            lp_bugs.add(next(g for g in m.groups() if g))
        for m in REVIEW_RE.finditer(text):
            reviews.add(next(g for g in m.groups() if g))
    else:
        for m in ISSUE_REF_RE.finditer(text):
            kind, sigil, num = m.group(1), m.group(2), m.group(3)
            if num == "0" or (m.start() > 0 and re.match(r"[\w`]", text[m.start() - 1])):
                continue
            if NON_ISSUE_PRECEDERS.search(text[max(0, m.start() - 12): m.start()]) or BACKTRACE_FRAME_RE.match(text, m.end()):
                continue
            prefix = text[max(0, m.start() - 25): m.start()]
            if re.search(r"[\w-]+/[\w-]+\s*(?:PR|MR)?\s*$", prefix):
                continue
            if sigil == "!" or kind == "MR":
                mr_refs.add(num)
            elif kind == "PR" and (repo.startswith("free5gc/") or is_gitlab):
                mr_refs.add(num)
            elif kind == "PR":
                mr_refs.add(num)
                issue_refs.add(num)
            else:
                issue_refs.add(num)
    for m in COMMIT_RE.finditer(text):
        if is_commit_hash(m.group(1)) and len(m.group(1)) >= 7:
            commits.add(m.group(1)[:7])
    for m in URL_REF_RE.finditer(text):
        if m.group(1).lower() in repo.lower():
            issue_refs.add(m.group(3))
    return {"issue": issue_refs, "mr": mr_refs, "commit": commits, "review": reviews, "lp_bug": lp_bugs}


def extract_all(rec):
    text = record_text(rec)
    specs, clauses = extract_specs(text)
    funcs, files = extract_code(text)
    generic_err, specific_err = extract_errors(text)
    refs = extract_refs(text, rec["source_id"])
    sbi = set(SBI_SERVICE_RE.findall(text)) | set(SBI_PATH_RE.findall(text))
    return {
        "nf": extract_dict(text, NF_RE),
        "iface": extract_dict(text, IFACE_RE) | ({"SBI"} if sbi else set()),
        "sbi_service": sbi,
        "neutron": extract_dict(text, NEUTRON_RE),
        "spec": specs,
        "spec_clause": clauses,
        "func": funcs,
        "file": files,
        "version": extract_versions(text),
        "config_key": extract_config_keys(text),
        "err_generic": generic_err,
        "err_specific": specific_err,
        "ref_issue": refs["issue"] | refs["lp_bug"],
        "ref_mr_pr": refs["mr"] | refs["review"],
        "ref_commit": refs["commit"],
    }


CATEGORIES = ["nf", "iface", "sbi_service", "spec", "spec_clause", "func", "file", "version", "config_key",
              "err_generic", "err_specific", "ref_issue", "ref_mr_pr", "ref_commit", "neutron"]


def extract_corpus(records):
    return {r["case_code"]: extract_all(r) for r in records}


def group_by(records, key):
    groups = defaultdict(list)
    for r in records:
        groups[r[key]].append(r)
    return groups
