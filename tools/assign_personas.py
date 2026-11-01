import hashlib

TEAM_WRITERS = {
    "RAN-CU": ["P01", "P02", "P03"],
    "RAN-DU": ["P04", "P05", "P06"],
    "UE": ["P05", "P06"],
    "CORE": ["P07", "P08", "P09"],
    "OAM": ["P10", "P11"],
    "PLATFORM": ["P11", "P12", "P13"],
}
LEAD = "P14"
LEAD_SHARE_PERCENT = 5


def assign(source_id, equipment):
    bucket = int(hashlib.sha256(source_id.encode()).hexdigest(), 16)
    if bucket % 100 < LEAD_SHARE_PERCENT:
        return LEAD
    writers = TEAM_WRITERS[equipment]
    return writers[(bucket // 100) % len(writers)]
