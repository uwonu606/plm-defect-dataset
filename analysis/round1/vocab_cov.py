import json,sys,re,collections
terms="AMF SMF UPF NRF UDM UDR AUSF PCF NSSF NEF BSF SCP SEPP MME SGW SGW-C SGW-U PGW PGW-C HSS PCRF gNB eNB CU-CP CU-UP CU DU RU UE RRC PDCP RLC MAC PHY SDAP NGAP F1AP E1AP S1AP X2AP XnAP NAS PFCP GTP GTP-U GTPv2 SCTP SBI Diameter NETCONF YANG O1 E2 FAPI eCPRI OVS OVN DPDK".split()
pat={t:re.compile(r'(?<![A-Za-z0-9])'+re.escape(t)+r'(?![A-Za-z0-9])',re.I) for t in terms}
by_origin=collections.Counter(); hit=collections.Counter(); termc=collections.Counter()
for l in open(sys.argv[1]):
    r=json.loads(l); loc=r.get('location') or ''
    head=' / '.join(loc.split(' / ')[:2])
    found=[t for t,p in pat.items() if p.search(head)]
    by_origin[r['origin']]+=1
    if found: hit[r['origin']]+=1
    for t in found: termc[t]+=1
for o in by_origin: print(o,hit[o],by_origin[o],round(hit[o]/by_origin[o],3))
print(len(terms),termc.most_common(25))
