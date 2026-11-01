import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "raw"
API = "https://api.launchpad.net/1.0"
PROJECTS = ["starlingx", "neutron"]
PAGE_SIZE = 75
WORKERS = 8


def http_json(url, retries=5):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            time.sleep(2 ** attempt * 3)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(2 ** attempt * 3)
    return None


def list_fixed_tasks(project):
    tasks = []
    start = 0
    while True:
        query = urllib.parse.urlencode({"ws.op": "searchTasks", "status": "Fix Released", "ws.size": PAGE_SIZE, "ws.start": start})
        page = http_json(f"{API}/{project}?{query}")
        if not page or not page.get("entries"):
            return tasks
        tasks.extend(page["entries"])
        start += PAGE_SIZE
        print(f"{project}: listed {len(tasks)}/{page.get('total_size', '?')}", flush=True)


def fetch_bug(task, project):
    bug = http_json(task["bug_link"])
    if not bug:
        return None
    messages = http_json(f"{task['bug_link']}/messages?ws.size=50") or {}
    return {
        "source": f"launchpad:{project}",
        "id": bug["id"],
        "title": bug["title"],
        "description": bug["description"],
        "tags": bug.get("tags", []),
        "created": bug.get("date_created"),
        "importance": task.get("importance"),
        "status": task.get("status"),
        "web_link": bug.get("web_link"),
        "messages": [m.get("content", "") for m in messages.get("entries", [])],
    }


def collect(project):
    path = RAW_DIR / f"launchpad__{project}.jsonl"
    if path.exists():
        return
    partial = path.with_suffix(".partial")
    done_ids = set()
    if partial.exists():
        done_ids = {json.loads(line)["id"] for line in partial.open(encoding="utf-8")}
    tasks = [t for t in list_fixed_tasks(project) if int(t["bug_link"].rsplit("/", 1)[1]) not in done_ids]
    with ThreadPoolExecutor(WORKERS) as pool, partial.open("a", encoding="utf-8") as out:
        for count, record in enumerate(pool.map(lambda t: fetch_bug(t, project), tasks), 1):
            if record:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            if count % 500 == 0:
                print(f"{project}: fetched {count}/{len(tasks)}", flush=True)
    partial.rename(path)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for project in sys.argv[1:] or PROJECTS:
        collect(project)
        print(f"done launchpad {project}", flush=True)


if __name__ == "__main__":
    main()
