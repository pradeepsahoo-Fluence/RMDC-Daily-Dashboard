#!/usr/bin/env python3
"""
RMDC multi-region dashboard – dual-button & dark-mode edition
-------------------------------------------------------------
• APAC / EMEA / USA cards
• Two buttons per card:
    – 🔄 Refresh  (reload latest CSV only)
    – ▶ Run       (start script + 1-hour lock)
• Dated CSVs  finaloutput_<region>_<YYYY-MM-DD>.csv
• 1-hour spam lock (LOCK_SECS = 3600)
• Green cells when Faulted Nodes Count == 0 or N/A
  Slow-blinking red cells when >0
• Summary site-count strip
• Compare / Graphs routes unchanged
• Dark-mode toggle in navbar
"""

# ─── Imports / paths ────────────────────────────────────────────────
from flask import Flask, render_template_string, request, redirect, url_for
import os, glob, datetime, subprocess, time, json, pytz, pandas as pd
from typing import Dict, Optional

app = Flask(__name__)

BASE_DIR = "/home/effone.psahoo/Desktop/nodedown/"
#CSV_DIR  = os.path.join(BASE_DIR, "output")
DEPLOY   = os.path.join(BASE_DIR, "deploy")
CSV_DIR  = os.path.join(DEPLOY, "output")
COMBINED_DIR = os.path.join(BASE_DIR, "output")

REGIONS: Dict[str, Dict[str, str]] = {
    "APAC": {"script": os.path.join(BASE_DIR, "apac.py")},
    "EMEA": {"script": os.path.join(BASE_DIR, "emea.py")},
    "USA" : {"script": os.path.join(BASE_DIR, "usa.py")},
}

LOCK_FILE = lambda r: os.path.join(DEPLOY, f"run_lock_{r.lower()}.timestamp")
LOCK_SECS = 3600                                # 1 hour
IST       = pytz.timezone("Asia/Kolkata")

#csv_by_date = lambda d: os.path.join(CSV_DIR, f"finaloutput_{d.strftime('%Y-%m-%d')}.csv")
csv_by_date = lambda d: os.path.join(COMBINED_DIR, f"finaloutput_{d.strftime('%Y-%m-%d')}.csv")
today_csv   = lambda: csv_by_date(datetime.datetime.now())
yest_csv    = lambda: csv_by_date(datetime.datetime.now() - datetime.timedelta(days=1))

# ─── Runtime caches ─────────────────────────────────────────────────
_tables: Dict[str, Optional[str]] = {r: None for r in REGIONS}
_last_loaded: Dict[str, Optional[str]] = {r: None for r in REGIONS}
_counts: Dict[str, int] = {r: 0 for r in REGIONS}

# ─── Helper functions ──────────────────────────────────────────────
def is_locked(region: str) -> bool:
    p = LOCK_FILE(region)
    return os.path.exists(p) and (time.time() - os.path.getmtime(p) < LOCK_SECS)

def touch_lock(region: str):
    os.makedirs(DEPLOY, exist_ok=True)
    with open(LOCK_FILE(region), "w") as f:
        f.write(str(time.time()))

def latest_csv(region: str) -> Optional[str]:
    today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
    preferred = os.path.join(CSV_DIR, f"finaloutput_{region.lower()}_{today}.csv")
    if os.path.exists(preferred):
        return preferred
    files = sorted(
        glob.glob(os.path.join(CSV_DIR, f"finaloutput_{region.lower()}_*.csv")),
        key=os.path.getmtime,
        reverse=True,
    )
    return files[0] if files else None

def colour_cell(val):
    try:
        if float(val) > 0:
            return "background-color:#f8d7da;animation:blinker 1.6s linear infinite;"
    except (ValueError, TypeError):
        pass
    return "background-color:#d4edda;"

def render_table(df: pd.DataFrame) -> str:
    df2 = df.copy()
    df2["Faulted Nodes Count"] = df2["Faulted Nodes Count"].fillna("N/A")
    df2 = df2.fillna("N/A")
    styler = (
        df2.style.applymap(colour_cell, subset=["Faulted Nodes Count"])
        .set_table_attributes('class="table table-striped table-bordered w-100"')
    )
    styler = styler.hide_index() if hasattr(styler, "hide_index") else styler.hide(axis="index")
    return styler.to_html() if hasattr(styler, "to_html") else styler.render()

def load_region(region: str):
    path = latest_csv(region)
    if not path:
        _tables[region], _counts[region] = None, 0
        return
    try:
        df = pd.read_csv(path)
        _tables[region] = render_table(df)
        _last_loaded[region] = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        _counts[region] = len(df)
    except Exception as e:
        _tables[region] = f"<div class='alert alert-danger'>Failed: {e}</div>"
        _counts[region] = 0

# ─── HTML / CSS / JS ────────────────────────────────────────────────
BOOT = (
    "<link rel='stylesheet' "
    "href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css'>"
    "<style>"
    "body{background:#f5f7fa;transition:background .3s,color .3s;}"
    ".card{border:none;border-radius:1rem;}"
    ".card-header{background:#eef1f4;border-bottom:none;border-radius:1rem 1rem 0 0;}"
    ".shadow-sm{box-shadow:0 .125rem .25rem rgba(0,0,0,.075)!important;}"
    "#summary .card{background:#fcfcfd;}"
    "@keyframes blinker{50%{opacity:.25;}}"
    "body.dark{background:#121212;color:#e4e4e4;}"
    "body.dark .card-header, body.dark #summary .card{background:#1e1e1e;}"
    "body.dark table{color:#e4e4e4;background:#121212;}"
    "body.dark th{background:#333!important;color:#fff;}"
    "body.dark td{background:#1e1e1e;}"
    "body.dark tbody tr:nth-of-type(even)>td{background:#202020;}"
    "body.dark .table-bordered>:not(caption)>*{border-color:#444;}"
    "</style>"
    "<script>"
    "function toggleTheme(){"
    "  document.body.classList.toggle('dark');"
    "  localStorage.setItem('theme',document.body.classList.contains('dark')?'dark':'light');"
    "}"
    "window.onload=function(){"
    "  if(localStorage.getItem('theme')==='dark'){document.body.classList.add('dark');}"
    "}"
    "</script>"
)

HEADER = (
    "<nav class='navbar navbar-dark bg-dark shadow-sm px-3'>"
    "  <span class='navbar-brand mb-0 h1'>RMDC Dashboard</span>"
    "  <div class='d-flex gap-2'>"
    "    <button class='btn btn-outline-light btn-sm' onclick='toggleTheme()'>🌓 Dark&nbsp;Mode</button>"
    "    <a href='{{ url_for(\"compare\") }}' class='btn btn-outline-light btn-sm'>📑 Compare</a>"
    "    <a href='{{ url_for(\"graphs\")  }}' class='btn btn-outline-info  btn-sm'>📈 Graphs</a>"
    "  </div>"
    "</nav>"
)

FOOTER = (
    "<footer class='bg-light text-center text-muted py-2 mt-4'>"
    "&copy;&nbsp;2025&nbsp;RMDC&nbsp;Monitoring</footer>"
)

PAGE = (
f"<html><head><title>RMDC Dashboard</title>{BOOT}</head><body>{HEADER}"
"<div class='container-fluid py-4'>"
"  <h2 class='text-primary fw-bold mb-3'>📊 Node-down Reports</h2>"
"  <div id='summary' class='row g-3 mb-4'>"
"    {% for reg, cnt in counts.items() %}"
"      <div class='col-6 col-md-4'>"
"        <div class='card shadow-sm text-center'>"
"          <div class='card-body py-3'>"
"            <h6 class='text-uppercase text-secondary fw-bold mb-1'>{{ reg }}</h6>"
"            <span class='display-6 fw-bold text-success'>{{ cnt }}</span>"
"            <small class='d-block text-muted'>sites</small>"
"          </div></div></div>{% endfor %}</div>"
"  {% if message %}<div class='alert alert-info shadow-sm'>{{ message }}</div>{% endif %}"
"  {% for r in regions %}"
"    <div class='card mb-4 shadow-sm'>"
"      <div class='card-header d-flex flex-wrap justify-content-between align-items-center'>"
"        <h5 class='mb-0 fw-bold'>{{ r }}</h5>"
"        <form method='post' class='d-flex gap-2 flex-wrap mb-0'>"
"          <input type='hidden' name='region' value='{{ r }}'>"
"          <button name='refresh_only' class='btn btn-outline-secondary btn-sm'>🔄 Refresh</button>"
"          <button name='run_script' class='btn btn-outline-primary btn-sm' {% if locked[r] %}disabled{% endif %}>▶ Run</button>"
"        </form>"
"      </div>"
"      <div class='card-body'>"
"        <div class='text-muted mb-2'>Last checked: {{ last_loaded.get(r,'N/A') }}</div>"
"        <div class='table-responsive'>"
"          {{ tables.get(r)|safe if tables.get(r) else '<div class=\"alert alert-warning\">No data.</div>' }}"
"        </div></div></div>{% endfor %}</div>"
f"{FOOTER}</body></html>"
)

# ─── Routes ──────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def dashboard():
    msg = ""
    if request.method == "POST":
        region = request.form.get("region")
        if region not in REGIONS:
            msg = "❌ Unknown region."
        elif "refresh_only" in request.form:
            load_region(region)
            msg = f"🔄 {region} refreshed."
        elif "run_script" in request.form:
            if is_locked(region):
                wait = int((LOCK_SECS - (time.time() - os.path.getmtime(LOCK_FILE(region)))) // 60) + 1
                msg = f"⚠️ {region} recently ran. Wait ≈{wait} min."
            else:
                subprocess.Popen(["python3", REGIONS[region]["script"]])
                touch_lock(region)
                msg = f"✅ {region} script started."
            load_region(region)

    for r in REGIONS:
        if _tables[r] is None:
            load_region(r)

    return render_template_string(
        PAGE,
        regions=REGIONS,
        tables=_tables,
        last_loaded=_last_loaded,
        locked={r: is_locked(r) for r in REGIONS},
        counts=_counts,
        message=msg,
    )

# Compare and Graphs routes stay unchanged (same as the code you posted)
# ────────────────────────────────────────────────────────────────────
@app.route("/compare", methods=["GET", "POST"])
def compare():
    today, yest = datetime.datetime.now(), datetime.datetime.now() - datetime.timedelta(days=1)
    df_today, df_yest = pd.read_csv(csv_by_date(today)), pd.read_csv(csv_by_date(yest))
    label = yest.strftime("%a-%b-%Y")

    def summary(df):
        tot, down = df["Total Nodes"].sum(), df["Faulted Nodes Count"].sum()
        return [tot, down, tot - down, f"{round((tot-down)/tot*100)}%"]

    s_today, s_yest = summary(df_today), summary(df_yest)
    today_df = df_today[["site name","region","Total Nodes",
                         "Faulted Nodes Count","Faulted Nodes","Remark"]]
    yest_df  = df_yest [["site name","Faulted Nodes Count","Faulted Nodes"]]
    yest_df.columns = ["site name",
                       f"Faulted Nodes Count ({label})",
                       f"Faulted Nodes ({label})"]
    comp_html = pd.merge(today_df, yest_df, on="site name", how="outer").fillna("N/A")\
                    .to_html(classes="table table-striped table-bordered w-100", index=False, escape=False)

    msg = ""
    if request.method == "POST":
        if "refresh_compare" in request.form:
            return redirect(url_for("compare"))

    COMP = (f"<html><head><title>Compare</title>{BOOT}</head><body>{HEADER}"
            "<div class='container-fluid my-4'>"
            "  <div class='d-flex justify-content-between flex-wrap mb-3'>"
            "    <h2 class='text-success'>📑 Compare Regions</h2>"
            "    <form method='post'><button name='refresh_compare' class='btn btn-outline-primary btn-sm'>🔄 Refresh</button></form>"
            "  </div>"
            "  <div class='row g-4'>"
            "    <div class='col-md-6'><h5 class='text-primary'>Today</h5>"
            "      <table class='table table-bordered w-100'><tr><th>Total</th><td>{{ t[0] }}</td></tr>"
            "        <tr><th>Down</th><td>{{ t[1] }}</td></tr><tr><th>Online</th><td>{{ t[2] }}</td></tr>"
            "        <tr><th>% Online</th><td>{{ t[3] }}</td></tr></table></div>"
            "    <div class='col-md-6'><h5 class='text-secondary'>Yesterday</h5>"
            "      <table class='table table-bordered w-100'><tr><th>Total</th><td>{{ y[0] }}</td></tr>"
            "        <tr><th>Down</th><td>{{ y[1] }}</td></tr><tr><th>Online</th><td>{{ y[2] }}</td></tr>"
            "        <tr><th>% Online</th><td>{{ y[3] }}</td></tr></table></div></div>"
            "  <h5 class='mt-4'>📋 Site Comparison</h5>"
            "  <div class='table-responsive'>{{ table|safe }}</div></div>"
            f"{FOOTER}</body></html>")
    return render_template_string(COMP, t=s_today, y=s_yest, table=comp_html, message=msg)

@app.route("/graphs")
def graphs():
    df_today, df_yest = pd.read_csv(today_csv()), pd.read_csv(yest_csv())
    merged = pd.merge(df_today[["site name","region","Faulted Nodes Count"]],
                      df_yest [["site name","Faulted Nodes Count"]],
                      on="site name", suffixes=("_today","_yesterday"), how="outer").fillna(0)
    plot_data = {"labels": merged["site name"].tolist(),
                 "today": merged["Faulted Nodes Count_today"].astype(int).tolist(),
                 "yesterday": merged["Faulted Nodes Count_yesterday"].astype(int).tolist(),
                 "regions": merged["region"].fillna("Unknown").tolist()}

    GRAPHS = (f"<html><head><title>Graphs</title>{BOOT}"
              "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>"
              "</head><body>"+HEADER+
              "<div class='container-fluid my-4'>"
              "  <div class='d-flex justify-content-between flex-wrap mb-3'>"
              "    <h2 class='text-success'>📈 Node-down Graphs</h2>"
              "    <a href='{{ url_for(\"dashboard\") }}' class='btn btn-outline-secondary btn-sm'>← Back</a>"
              "  </div><div id='chartDiv' style='width:100%;height:600px;'></div></div>"
              "<script>"
              "const raw={{ data|safe }};"
              "Plotly.newPlot('chartDiv',["
              "  {x:raw.labels,y:raw.today,type:'bar',name:'Today'},"
              "  {x:raw.labels,y:raw.yesterday,type:'bar',name:'Yesterday'}],"
              "  {barmode:'group',xaxis:{title:'Site'},yaxis:{title:'Faulted Nodes'},autosize:true});"
              "</script>"+FOOTER+"</body></html>")
    return render_template_string(GRAPHS, data=json.dumps(plot_data))

# ─── Entrypoint ───────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(DEPLOY, exist_ok=True)
    app.run(host="0.0.0.0", port=3000, debug=False)