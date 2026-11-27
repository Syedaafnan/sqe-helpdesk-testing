"""Lighthouse (accessibility, best practices, SEO) on the key screen of each use case.

    python manage.py demo_data --reset && python tests/team/seed/seed_butter_bean.py
    python manage.py runserver 0.0.0.0:8080
    python tests/team/e2e/lighthouse_screens.py

UC-1  public submit form          /tickets/submit/          (anonymous)
UC-2  staff submit form           /tickets/submit/          (staff afnan)
UC-3  staff ticket page           /tickets/<id>/            (staff arooj)
UC-4  customer ticket page        /view/?ticket=...&key=... (customer link)

Staff screens: the script logs in with the normal login form, then gives the
session cookie to Lighthouse as an extra header. Reports are written to
docs/team/evidence/accessibility/lighthouse_<screen>.report.{html,json}, and
lighthouse_screens_summary.txt merges them with the axe-core survey so an issue
found by both tools is counted once.

LIGHTHOUSE overrides the command (default: npx -y lighthouse@12.2.1).
"""

import json
import os
import re
import shlex
import subprocess
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demodesk.config.settings")

import django  # noqa: E402

django.setup()

from helpdesk.models import Ticket  # noqa: E402
from tests.team.seed import content as cafe  # noqa: E402

BASE = os.environ.get("E2E_BASE_URL", "http://localhost:8080").rstrip("/")
OUT = Path("docs/team/evidence/accessibility")
TMP = Path(".lighthouse_tmp")
CATEGORIES = "accessibility,best-practices,seo"


def session_cookie(username):
    """Log in through the real login form and return the session cookie."""
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    page = opener.open(f"{BASE}/login/").read().decode()
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)
    data = urllib.parse.urlencode(
        {"username": username, "password": cafe.PASSWORD, "csrfmiddlewaretoken": token, "next": "/"}
    ).encode()
    req = urllib.request.Request(f"{BASE}/login/", data=data, headers={"Referer": f"{BASE}/login/"})
    opener.open(req)
    cookies = {c.name: c.value for c in jar}
    assert "sessionid" in cookies, f"login failed for {username}"
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def screens():
    ticket = Ticket.objects.get(queue__slug=cafe.MAIN_QUEUE_SLUG,
                                title="Wi-Fi dies every time someone starts a match")
    view = urllib.parse.urlencode({"ticket": ticket.ticket_for_url,
                                   "email": ticket.submitter_email, "key": ticket.secret_key})
    return [
        ("uc1_public_submit", "/tickets/submit/", None, "public_submit"),
        ("uc2_staff_submit", "/tickets/submit/", cafe.W1_STAFF, "staff_submit"),
        ("uc3_staff_ticket", f"/tickets/{ticket.id}/", cafe.W2_STAFF, "staff_ticket"),
        ("uc4_customer_ticket", f"/view/?{view}", None, "customer_ticket"),
    ]


def run_lighthouse(name, path, user):
    TMP.mkdir(exist_ok=True)
    headers = TMP / f"{name}.json"
    headers.write_text(json.dumps({"Cookie": session_cookie(user)} if user else {}))
    launcher = shlex.split(os.environ.get("LIGHTHOUSE", "npx -y lighthouse@12.2.1"))
    url = BASE + path
    if launcher[0].lower().startswith("cmd"):  # run through Windows cmd.exe (e.g. from WSL)
        url = url.replace("&", "^&")
    cmd = launcher + [
        url,
        f"--only-categories={CATEGORIES}",
        "--output=json", "--output=html",
        f"--output-path={(OUT / f'lighthouse_{name}').as_posix()}",
        f"--extra-headers={headers.as_posix()}",
        "--chrome-flags=--headless=new",
        "--quiet",
    ]
    subprocess.run(cmd, check=True)
    return json.loads((OUT / f"lighthouse_{name}.report.json").read_text(encoding="utf-8"))


def failing(report):
    """(category, audit id, title, first elements) for every failed audit."""
    out = []
    for cat_id, cat in report["categories"].items():
        for ref in cat["auditRefs"]:
            a = report["audits"][ref["id"]]
            if a["scoreDisplayMode"] in ("binary", "numeric") and a["score"] is not None and a["score"] < 1:
                items = (a.get("details") or {}).get("items", [])
                nodes = [i["node"].get("selector", "") for i in items if isinstance(i.get("node"), dict)]
                out.append((cat_id, ref["id"], a["title"], nodes[:3]))
    return out


def main():
    os.chdir(ROOT)
    lines = [f"Lighthouse {CATEGORIES} on each use case's key screen ({BASE}, mobile emulation)", ""]
    seen = {}
    for name, path, user, axe_name in screens():
        report = run_lighthouse(name, path, user)
        scores = {k: round(v["score"] * 100) for k, v in report["categories"].items()}
        lines.append(f"{name}  {path.split('?')[0]}  as {user or 'anonymous'}: "
                     + ", ".join(f"{k} {v}" for k, v in scores.items()))
        for cat, audit, title, nodes in failing(report):
            seen.setdefault(audit, {"title": title, "category": cat, "tools": set(), "screens": {}})
            seen[audit]["tools"].add("Lighthouse")
            seen[audit]["screens"].setdefault(name, nodes)
        axe_file = OUT / f"axe_survey_{axe_name}_after.json"
        if not axe_file.exists():
            axe_file = OUT / f"axe_survey_{axe_name}_current.json"
        if axe_file.exists():
            for v in json.loads(axe_file.read_text()):
                seen.setdefault(v["rule"], {"title": v["help"], "category": "accessibility",
                                            "tools": set(), "screens": {}})
                seen[v["rule"]]["tools"].add("axe-core")
                seen[v["rule"]]["screens"].setdefault(name, [t[0] for t in v["targets"][:3]])
    lines += ["", f"Distinct issues (an issue found by both tools counted once): {len(seen)}", ""]
    for rule, info in sorted(seen.items()):
        lines.append(f"- {rule} [{info['category']}; {' + '.join(sorted(info['tools']))}]: {info['title']}")
        for screen, nodes in info["screens"].items():
            lines.append(f"    {screen}: {', '.join(nodes) if nodes else '(page level)'}")
    (OUT / "lighthouse_screens_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f in TMP.glob("*.json"):
        f.unlink()
    TMP.rmdir()
    print("\n".join(lines))


if __name__ == "__main__":
    main()
