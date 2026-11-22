# Baseline and Environment

## Upstream reference

| Item | Value |
|---|---|
| System | django-helpdesk (Django-based helpdesk / ticket management MIS) |
| Upstream URL | https://github.com/django-helpdesk/django-helpdesk |
| Licence | BSD-3-Clause (see `LICENSE`) |
| Baseline commit | `7bf832c76dc1a8b89ed43be25c0429cd346d360d` (19 Nov 2026, "Merge pull request #1528") |
| Git tag | `baseline` |
| Team repository | https://github.com/Syedaafnan/sqe-helpdesk-testing |

All commits up to and including tag `baseline` are upstream django-helpdesk.
Team work starts after it. List team-only commits with:

```bash
git log --oneline baseline..main
```

Upstream tests live in `tests/` and are **not** part of our submission.
All team tests live in `tests/team/`.

## Environment

| Component | Version |
|---|---|
| Host OS | Windows 11 Pro 10.0.26200 |
| Runtime OS | Ubuntu 24.04 under WSL 2 (see note below) |
| Python | 3.12 |
| Django | 6.1.3 |
| Django REST Framework | 3.18.3 |
| Database | SQLite (`demodesk/db.sqlite3`) |
| Node.js | 24.11.0 (Playwright, Lighthouse) |
| Docker | 28.5.2 (SonarQube, OWASP ZAP) |

**Why WSL:** Windows Smart App Control (enabled on the host) blocks unsigned
native Python extensions such as `nh3` and `Pillow`, which django-helpdesk
needs. Running Python inside WSL Ubuntu avoids this without weakening host
security. mutmut also requires a POSIX system.

## One-time install (WSL Ubuntu terminal)

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip
cd "/mnt/c/Users/shazi/Desktop/sqe final project/django-helpdesk"
python3 -m venv ~/venvs/helpdesk
source ~/venvs/helpdesk/bin/activate
pip install --upgrade pip
pip install -e .
pip install -r tests/team/requirements.txt
```

The virtual environment lives in the WSL home folder (`~/venvs/helpdesk`) because
file I/O on `/mnt/c` is slow for many small files.

If you don't know the Ubuntu password, install the system packages as root from
**Windows PowerShell** instead:
`wsl -d Ubuntu-24.04 -u root -- bash -c "apt update && apt install -y python3-venv python3-pip"`

### Front-end libraries (Bootstrap, jQuery, DataTables, Font Awesome)

Without this step the UI renders unstyled and its JavaScript doesn't run.

```powershell
# Windows PowerShell, in the repository folder
npm install --no-package-lock --no-audit --no-fund
```

```bash
# WSL: the Makefile needs `node`; reuse the Windows binary
mkdir -p ~/bin && ln -sf "/mnt/c/Program Files/nodejs/node.exe" ~/bin/node
export PATH="$HOME/bin:$PATH"
make static-vendor      # copies node_modules/* into src/helpdesk/static/helpdesk/vendor/
```

`node_modules/` and the vendor folder are git-ignored, so each machine repeats this step.

## Seed test data

```bash
source ~/venvs/helpdesk/bin/activate
cd "/mnt/c/Users/shazi/Desktop/sqe final project/django-helpdesk"
python manage.py migrate --noinput
python manage.py loaddata emailtemplate.json demo.json
python manage.py demo_data
```

Result (verified 2026-11-21): *"Demo data generated: 141 tickets, 586 follow-ups, 6 users."*
`demo_data` uses a fixed random seed (`--seed 1476`), so every seed produces the same records.

### Test accounts (all share the password `Pa33w0rd`)

| Username | Role | Queues |
|---|---|---|
| `admin` | Superuser / staff | all |
| `alice` | Staff agent | IT, DH |
| `bruno` | Staff agent | SP, BIL |
| `chloe` | Staff agent | WEB, DH, SP |
| `kenji` | Staff agent | IT, WEB |
| `sam` | Non-staff submitter (`sam.rivera@example.com`) | none |

## Start the application

```bash
python manage.py runserver 0.0.0.0:8080
```

Open http://localhost:8080 from Windows.

| URL | Purpose |
|---|---|
| `/` | Public portal |
| `/tickets/submit/` | Public ticket submission (Workflow 1) |
| `/view/?ticket=...&email=...&key=...` | Submitter's ticket view and update (Workflow 2, submitter) |
| `/tickets/<id>/` | Staff ticket view and update (Workflow 2, staff) |
| `/api/tickets/` | REST API, tickets |
| `/api/followups/` | REST API, follow-ups (status changes) |
| `/admin/` | Django admin |

## Reset between runs

```bash
python manage.py demo_data --reset
```

`--reset` flushes the database, reloads both fixtures and regenerates the same seeded
data. For a completely fresh database (e.g. after a schema change):

```bash
rm -f demodesk/db.sqlite3
python manage.py migrate --noinput
python manage.py loaddata emailtemplate.json demo.json
python manage.py demo_data
```

Unit and API tests (pytest) do not use this database. pytest-django creates a
fresh test database for every run and rolls back each test, so no reset is
needed for them.
