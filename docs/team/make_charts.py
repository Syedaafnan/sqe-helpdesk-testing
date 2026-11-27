"""Draws the report charts in black and white (report rule: no colour in charts).

    pip install matplotlib
    python docs/team/make_charts.py

Writes docs/team/evidence/pareto.png, fishbone_def10.png, fishbone_def13.png
and performance_p95.png (from the k6 summaries, if present).
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

# Root-cause categories from DEFECTS.md
PARETO = [
    ("Rule enforced\non one path\nonly", 5),
    ("Input\nvalidation /\nAPI contract", 4),
    ("Missing\nhardening", 3),
    ("Transaction /\nidempotency", 2),
    ("Accessibility\nmarkup", 1),
    ("N+1\nqueries", 1),
]


def pareto():
    labels, counts = zip(*PARETO)
    total = sum(counts)
    cumulative, run = [], 0
    for c in counts:
        run += c
        cumulative.append(100 * run / total)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bars = ax.bar(labels, counts, color="white", edgecolor="black", hatch="//")
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c + 0.1, str(c), ha="center")
    ax.set_ylabel("Number of defects")
    ax.set_ylim(0, max(counts) + 1.5)
    ax2 = ax.twinx()
    ax2.plot(labels, cumulative, color="black", marker="o")
    for i, y in enumerate(cumulative):
        ax2.text(i + 0.18, y - 6, f"{y:.0f}%", ha="left",
                 bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
    ax2.axhline(80, color="black", linestyle="--", linewidth=0.8)
    ax2.text(len(labels) - 0.5, 81, "80 %", ha="right")
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("Cumulative %")
    ax.set_title(f"Pareto of defects by root-cause category (n = {total})")
    fig.tight_layout()
    fig.savefig(EVIDENCE / "pareto.png", dpi=200)
    plt.close(fig)


def fishbone(name, effect, causes):
    fig, ax = plt.subplots(figsize=(14, 6.2))
    ax.set_xlim(0, 16.5)
    ax.set_ylim(0, 6)
    ax.axis("off")
    spine_end = 13.0
    ax.annotate("", xy=(spine_end, 3), xytext=(0.3, 3),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=2))
    ax.text(spine_end + 0.15, 3, effect, va="center", ha="left", fontsize=10, fontweight="bold",
            bbox=dict(boxstyle="square", fc="white", ec="black"))
    joints = [4.2, 8.2, 12.2]          # where each bone meets the spine
    for i, (cat, items) in enumerate(causes):
        top = i < 3
        jx = joints[i % 3]
        y_end = 5.4 if top else 0.6
        x_end = jx - 1.3                # bones slant back towards the tail
        ax.plot([x_end, jx], [y_end, 3], color="black", lw=1.4)
        ax.text(x_end, y_end + (0.18 if top else -0.32), cat, ha="center", fontweight="bold", fontsize=10)
        for j, item in enumerate(items):
            t = (j + 1) / (len(items) + 1)
            bx = x_end + t * (jx - x_end)
            by = y_end + t * (3 - y_end)
            ax.plot([bx - 0.5, bx], [by, by], color="black", lw=0.7)
            ax.text(bx - 0.58, by, item, ha="right", va="center", fontsize=8)
    ax.set_title(f"Fishbone diagram: {name}", fontweight="bold")
    fig.tight_layout()
    fig.savefig(EVIDENCE / f"fishbone_{name.split()[0].lower().replace('-', '')}.png", dpi=200)
    plt.close(fig)


def performance():
    rows = []
    for run in ("1u_run1", "1u_run2", "5u_run1", "5u_run2"):
        f = EVIDENCE / "performance" / f"k6_{run}.json"
        if not f.exists():
            return
        m = json.loads(f.read_text())["metrics"]
        rows.append((run, m["http_req_duration{kind:read}"]["values"]["p(95)"],
                     m["http_req_duration{kind:write}"]["values"]["p(95)"]))
    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = range(len(rows))
    w = 0.38
    ax.bar([i - w / 2 for i in x], [r[1] for r in rows], w, color="white", edgecolor="black", hatch="..", label="reads p95")
    ax.bar([i + w / 2 for i in x], [r[2] for r in rows], w, color="white", edgecolor="black", hatch="//", label="writes p95")
    ax.axhline(500, color="black", linestyle="--", linewidth=0.8)
    ax.text(-0.55, 560, "read target 500 ms", ha="left", fontsize=8, bbox=dict(fc="white", ec="none", pad=1))
    ax.axhline(1500, color="black", linestyle=":", linewidth=0.8)
    ax.text(-0.55, 1560, "write target 1500 ms", ha="left", fontsize=8, bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_xticks(list(x))
    ax.set_xticklabels([r[0].replace("_", " ") for r in rows])
    ax.set_ylabel("p95 response time (ms)")
    ax.set_title("k6: p95 response time per run")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(EVIDENCE / "performance_p95.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    pareto()
    fishbone("DEF-10 status rule only in the browser", "Staff form saves\na disallowed status", [
        ("People", ["Disabled radio taken as enforcement", "Different authors per view"]),
        ("Method", ["No 'all write paths' checklist", "Review of the diff only"]),
        ("Machine (code)", ["Rule only in the template", "No shared rule function", "update_ticket accepts any code"]),
        ("Material (requirements)", ["Flow is a setting, not a model rule", "Docs silent on server enforcement"]),
        ("Measurement (testing)", ["Tests send only offered values", "No negative direct-POST tests"]),
        ("Environment", ["Users never edit requests", "Browser hides it in normal use"]),
    ])
    fishbone("DEF-13 non-atomic status change", "Status saved,\nhistory lost", [
        ("People", ["SQLite assumed never to fail"]),
        ("Method", ["No 'one action = one transaction' rule", "Retry semantics not designed"]),
        ("Machine (code)", ["ticket.save() before follow_up.save()", "No transaction.atomic", "Retry compares stored status"]),
        ("Material (requirements)", ["FR-10 not linked to consistency"]),
        ("Measurement (testing)", ["No fault-injection tests", "Only happy-path tests"]),
        ("Environment", ["Single-user demo rarely locks", "Production DB timeouts likely"]),
    ])
    performance()
    print("charts written to", EVIDENCE)
