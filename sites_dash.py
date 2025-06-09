"""
sites_dash.py  –  blueprint that turns site-level CSV reports into a mini-dashboard

• Overview      /sites
• Per-site view /sites/<site>
Expected filename pattern:
    <site>_device_status_YYYYMMDDHHMMSS.csv
Expected CSV header (exact case):
    time,Device name,Ping,SSH,Telnet
"""

from pathlib import Path
from time import time
import pandas as pd
from flask import Blueprint, render_template, abort
from typing import Dict


# ─── CONFIG ─────────────────────────────────────────────────────────
CSV_DIR = Path("/home/effone.psahoo/Desktop/cube/sites_output")   # adjust if needed
STALE_MINUTES = 60                                                # grey-out threshold
# ───────────────────────────────────────────────────────────────────

bp = Blueprint("sites", __name__, template_folder="templates")


# ─── helpers ───────────────────────────────────────────────────────
def _latest_csvs() -> Dict[str, Path]:
    """Return {site: Path(latest_csv)} using mtime to choose the newest."""
    latest: dict[str, Path] = {}
    for f in CSV_DIR.glob("*_device_status_*.csv"):
        site = f.name.split("_device_status_", 1)[0]
        if site not in latest or f.stat().st_mtime > latest[site].stat().st_mtime:
            latest[site] = f
    return latest


# ─── routes ────────────────────────────────────────────────────────
@bp.route("/sites")
def index():
    now = time()
    rows = []
    for site, csv_path in _latest_csvs().items():
        df = pd.read_csv(csv_path)
        offline = (df["Ping"] != "Reachable") | (df["SSH"] != "Reachable") | (df["Telnet"] != "Reachable")
        total, down = len(df), int(offline.sum())
        avail = round(100 * (total - down) / total, 1) if total else 0
        rows.append(
            dict(site=site,
                 updated=csv_path.stat().st_mtime,
                 stale=((now - csv_path.stat().st_mtime) / 60) > STALE_MINUTES,
                 total=total, down=down, avail=avail)
        )
    rows.sort(key=lambda r: r["site"].lower())
    return render_template("sites_index.html", rows=rows, stale=STALE_MINUTES)


@bp.route("/sites/<site>")
def detail(site: str):
    csv_map = _latest_csvs()
    if site not in csv_map:
        abort(404, f"No data for site: {site}")

    df = pd.read_csv(csv_map[site])
    df["Offline"] = (df["Ping"] != "Reachable") | (df["SSH"] != "Reachable") | (df["Telnet"] != "Reachable")
    total, down = len(df), int(df["Offline"].sum())
    avail = round(100 * (total - down) / total, 1) if total else 0

    total, down = len(df), int(df["Offline"].sum())
    avail = round(100 * (total - down) / total, 1) if total else 0

    # ── NEW: how many completely OK (all three checks reachable) ──
    good = int(((df["Ping"] == "Reachable") &
                (df["SSH"]  == "Reachable") &
                (df["Telnet"] == "Reachable")).sum())

    bad = total - good           # any check failed

    return render_template("sites_detail.html",
                           site=site,
                           records=df.to_dict("records"),
                           total=total, down=bad, avail=avail,
                           good=good,
                           bad=bad,
                           )