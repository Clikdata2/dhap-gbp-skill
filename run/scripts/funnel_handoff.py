#!/usr/bin/env python3
"""DHAP GBP funnel handoff (v16.7): after the seven files are built, send the two pages to the funnel team.

Puts the dealer's DHAP HTML, Digital Health Alert HTML and an info.json in one folder named <slug>-<MM-DD-YY>/ and
opens a pull request with it on Clikdata2/dhap-funnel-handoff, so every finished run reaches the funnel team the same
way, whoever runs it. info.json holds the dealership name, slug, city and state, website, report ID and audit date:

  {"dealership_name": "James Mitsubishi Rome", "slug": "james-mitsubishi-rome", "city": "Rome", "state": "NY",
   "website": "http://jamesmitsubishi.com", "report_id": "GBP-JMRNY-1126", "date": "2026-11-02"}

The slug and date come from the built file names (<slug>_dhap_<MM-DD-YY>.html), the name and date from the evidence,
city and state from the website's address (evidence nap.site.address), the report ID from the content JSON, and the
website from --website (the address the run was given).

Needs git and the GitHub CLI (`gh auth login` once). With write access the branch goes straight to the handoff
repository; without it, the script forks the repository to your account and opens the pull request from the fork.
It never overwrites: if the dealer's folder for that date is already on main, or its branch already exists, it stops.

Usage:
  python3 funnel_handoff.py --evidence evidence.json --content content.json --out OUT --website https://dealer.com
  python3 funnel_handoff.py ... --no-pr --stage DIR     # build the folder in DIR only (a dry run, no GitHub)
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HANDOFF_REPO = "Clikdata2/dhap-funnel-handoff"
CACHE = Path.home() / ".dhap-funnel-handoff"


def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def find(o, key):
    """First string value stored under `key` anywhere in a JSON tree."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key and isinstance(v, str) and v:
                return v
            r = find(v, key)
            if r:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find(v, key)
            if r:
                return r
    return None


def build_info(ev, content, slug, date_mmddyy, website):
    name = ev.get("dealer")
    if not name:
        sys.exit("evidence has no dealer name")
    addr = ((ev.get("nap") or {}).get("site") or {}).get("address") or ""
    m = re.search(r",\s*([^,]+),\s*([A-Z]{2})\b", addr)
    if m:
        city, state = m.group(1).strip(), m.group(2)
    else:
        cs = find(ev.get("ai_visibility") or {}, "city") or ""
        m = re.match(r"\s*(.+?),\s*([A-Z]{2})\s*$", cs)
        if not m:
            sys.exit(f"could not read city and state from the website address {addr!r}")
        city, state = m.group(1), m.group(2)
    report_id = find(content, "report_id")
    if not report_id:
        sys.exit("content JSON has no report_id")
    mm, dd, yy = date_mmddyy.split("-")
    date = f"20{yy}-{mm}-{dd}"
    if ev.get("audit_date") and ev["audit_date"] != date:
        print(f"note: file date {date} differs from evidence audit_date {ev['audit_date']}; using the file date")
    return {"dealership_name": name, "slug": slug, "city": city, "state": state,
            "website": website, "report_id": report_id, "date": date}


def pages(out):
    dhaps = sorted(Path(out).glob("*_dhap_*.html"))
    if len(dhaps) != 1:
        sys.exit(f"expected one <slug>_dhap_<MM-DD-YY>.html in {out}, found {len(dhaps)}")
    m = re.match(r"(.+)_dhap_(\d\d-\d\d-\d\d)\.html$", dhaps[0].name)
    if not m:
        sys.exit(f"unexpected DHAP file name {dhaps[0].name}")
    slug, dt = m.groups()
    alert = Path(out) / f"{slug}_health-alert_{dt}.html"
    if not alert.exists():
        sys.exit(f"missing {alert.name} in {out}")
    return slug, dt, dhaps[0], alert


def write_folder(dest, dhap, alert, info):
    dest.mkdir(parents=True)
    shutil.copy2(dhap, dest / dhap.name)
    shutil.copy2(alert, dest / alert.name)
    (dest / "info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


def open_pr(folder, dhap, alert, info):
    if run(["gh", "auth", "status"], check=False).returncode != 0:
        sys.exit("GitHub CLI is not signed in: run `gh auth login`, then run this again")
    if not (CACHE / ".git").exists():
        run(["gh", "repo", "clone", HANDOFF_REPO, str(CACHE)])
    run(["git", "fetch", "-q", "origin"], cwd=CACHE)
    run(["git", "checkout", "-q", "-B", "main", "origin/main"], cwd=CACHE)
    if (CACHE / folder).exists():
        sys.exit(f"{folder}/ is already on main in {HANDOFF_REPO}; nothing sent (never overwritten)")
    branch = f"add-{folder}"
    can_push = run(["gh", "api", f"repos/{HANDOFF_REPO}", "--jq", ".permissions.push"]).stdout.strip() == "true"
    if can_push:
        remote, head = "origin", branch
    else:
        login = run(["gh", "api", "user", "--jq", ".login"]).stdout.strip()
        run(["gh", "repo", "fork", HANDOFF_REPO, "--clone=false"])
        fork_url = f"https://github.com/{login}/{HANDOFF_REPO.split('/')[1]}.git"
        if run(["git", "remote", "get-url", "fork"], cwd=CACHE, check=False).returncode != 0:
            run(["git", "remote", "add", "fork", fork_url], cwd=CACHE)
        remote, head = "fork", f"{login}:{branch}"
    if run(["git", "ls-remote", "--exit-code", "--heads", remote, branch], cwd=CACHE, check=False).returncode == 0:
        sys.exit(f"branch {branch} already exists on {remote}; a pull request for this report was already sent")
    run(["git", "checkout", "-q", "-b", branch], cwd=CACHE)
    write_folder(CACHE / folder, dhap, alert, info)
    run(["git", "add", folder], cwd=CACHE)
    title = f"Add {info['dealership_name']} DHAP handoff ({folder[-8:]})"
    run(["git", "commit", "-q", "-m", title], cwd=CACHE)
    run(["git", "push", "-q", "-u", remote, branch], cwd=CACHE)
    body = (f"Adds `{folder}/`: the DHAP HTML, the Digital Health Alert HTML and `info.json`.\n\n"
            f"```json\n{json.dumps(info, indent=2)}\n```\n\n"
            "Sent by `run/scripts/funnel_handoff.py` (DHAP GBP). The DHAP funnel link is still the "
            "`REPLACE_WITH_DHAP_FUNNEL_LINK` placeholder, added by hand.")
    pr = run(["gh", "pr", "create", "--repo", HANDOFF_REPO, "--base", "main", "--head", head,
              "--title", title, "--body", body]).stdout.strip()
    run(["git", "checkout", "-q", "main"], cwd=CACHE)
    return pr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--out", required=True, help="folder holding the built <slug>_dhap_ and _health-alert_ HTML")
    ap.add_argument("--website", required=True, help="the dealer's website as given for the run")
    ap.add_argument("--no-pr", action="store_true", help="only build the folder (use with --stage)")
    ap.add_argument("--stage", help="with --no-pr: where to build the folder")
    a = ap.parse_args()
    ev = json.loads(Path(a.evidence).read_text(encoding="utf-8"))
    content = json.loads(Path(a.content).read_text(encoding="utf-8"))
    slug, dt, dhap, alert = pages(a.out)
    info = build_info(ev, content, slug, dt, a.website)
    folder = f"{slug}-{dt}"
    if a.no_pr:
        if not a.stage:
            sys.exit("--no-pr needs --stage DIR")
        dest = Path(a.stage) / folder
        if dest.exists():
            sys.exit(f"{dest} already exists; not overwritten")
        write_folder(dest, dhap, alert, info)
        print(f"built {dest} (no pull request)")
    else:
        print(f"FUNNEL HANDOFF OK: {open_pr(folder, dhap, alert, info)}")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
