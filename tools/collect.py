import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "raw"

GITHUB_REPOS = [
    "open5gs/open5gs",
    "free5gc/free5gc",
    "magma/magma",
    "srsran/srsRAN_Project",
    "srsran/srsRAN_4G",
    "duranta-project/openairinterface5g",
]

GITLAB_PROJECTS = [
    ("https://gitlab.com/api/v4", "ocudu/ocudu"),
    ("https://gitlab.eurecom.fr/api/v4", "oai/openairinterface5g"),
]

ISSUE_QUERY = """
query($owner:String!, $name:String!, $cursor:String) {
  repository(owner:$owner, name:$name) {
    issues(first:40, after:$cursor, states:CLOSED, orderBy:{field:CREATED_AT, direction:ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title body url createdAt closedAt stateReason
        labels(first:10) { nodes { name } }
        comments(first:30) { nodes { author { login } body } }
        timelineItems(first:15, itemTypes:[CLOSED_EVENT, CROSS_REFERENCED_EVENT]) {
          nodes {
            __typename
            ... on ClosedEvent { closer { __typename ... on PullRequest { number title body url merged } ... on Commit { oid message url } } }
            ... on CrossReferencedEvent { source { __typename ... on PullRequest { number title body url merged repository { nameWithOwner } } } }
          }
        }
      }
    }
  }
}
"""


def http_json(url, headers=None, data=None, retries=4):
    for attempt in range(retries):
        request = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (401, 403, 404) and attempt == retries - 1:
                return None
            if error.code in (401, 404):
                return None
            time.sleep(2 ** attempt * 5)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 ** attempt * 5)
    return None


def write_jsonl(path, records):
    with path.open("a", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")


def collect_github(repo, token):
    path = RAW_DIR / f"github__{repo.replace('/', '__')}.jsonl"
    if path.exists():
        return
    partial = path.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    owner, name = repo.split("/")
    cursor = None
    headers = {"Authorization": f"bearer {token}", "Content-Type": "application/json"}
    while True:
        payload = json.dumps({"query": ISSUE_QUERY, "variables": {"owner": owner, "name": name, "cursor": cursor}}).encode()
        result = http_json("https://api.github.com/graphql", headers, payload)
        if not result or "data" not in result or not result["data"]["repository"]:
            print(f"github {repo}: query failed {result and result.get('errors')}", file=sys.stderr)
            return
        issues = result["data"]["repository"]["issues"]
        write_jsonl(partial, [dict(node, source=f"github:{repo}") for node in issues["nodes"]])
        if not issues["pageInfo"]["hasNextPage"]:
            break
        cursor = issues["pageInfo"]["endCursor"]
    partial.rename(path)


def collect_gitlab(api, project):
    path = RAW_DIR / f"gitlab__{project.replace('/', '__')}.jsonl"
    if path.exists():
        return
    partial = path.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    encoded = urllib.parse.quote(project, safe="")
    page = 1
    while True:
        issues = http_json(f"{api}/projects/{encoded}/issues?state=closed&per_page=100&page={page}")
        if not issues:
            break
        records = []
        for issue in issues:
            iid = issue["iid"]
            issue["related_merge_requests"] = http_json(f"{api}/projects/{encoded}/issues/{iid}/related_merge_requests") or []
            issue["notes"] = http_json(f"{api}/projects/{encoded}/issues/{iid}/notes?per_page=50&sort=asc") or []
            issue["source"] = f"gitlab:{project}"
            records.append(issue)
        write_jsonl(partial, records)
        page += 1
    partial.rename(path)


def collect_redhat_doc_text():
    path = RAW_DIR / "bugzilla__redhat_doc_text.jsonl"
    if path.exists():
        return
    partial = path.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    fields = "id,summary,product,component,version,cf_fixed_in,cf_release_notes,creation_time,status,resolution"
    offset = 0
    while True:
        query = urllib.parse.urlencode({
            "f1": "cf_release_notes", "o1": "substring", "v1": "Consequence:",
            "include_fields": fields, "limit": 20, "offset": offset, "order": "bug_id",
        })
        result = http_json(f"https://bugzilla.redhat.com/rest/bug?{query}")
        bugs = (result or {}).get("bugs", [])
        if not bugs:
            break
        write_jsonl(partial, [dict(bug, source="bugzilla:redhat") for bug in bugs])
        offset += len(bugs)
    partial.rename(path)


def download_mic_casebook():
    path = RAW_DIR / "mic_jp__incident_casebook.xlsx"
    if not path.exists():
        urllib.request.urlretrieve("https://www.soumu.go.jp/main_content/001089868.xlsx", path)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    download_mic_casebook()
    for repo in GITHUB_REPOS:
        collect_github(repo, token)
        print(f"done github {repo}", flush=True)
    for api, project in GITLAB_PROJECTS:
        collect_gitlab(api, project)
        print(f"done gitlab {project}", flush=True)
    collect_redhat_doc_text()
    print("done bugzilla redhat", flush=True)


if __name__ == "__main__":
    main()
