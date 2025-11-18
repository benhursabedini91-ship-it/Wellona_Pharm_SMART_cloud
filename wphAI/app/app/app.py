import os, sys, traceback, io, datetime
# ---- FORCE UTF-8 for all prints/logs (fix UnicodeEncodeError) ----
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from flask import Flask, send_file, render_template_string, redirect, url_for, Response
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault("OB_OUTDIR", r"C:\Wellona\wphAI\out\orders")
import order_brain

APP_TITLE = "Wellona Order Brain – Mini UI"
OUTDIR = os.environ.get("OB_OUTDIR", r"C:\Wellona\wphAI\out\orders")
WORKDIR = os.path.join(os.path.dirname(__file__), "work")
LOGDIR = r"C:\Wellona\wphAI\logs"
LOGFILE = os.path.join(LOGDIR, "ui_waitress.log")

TPL = '''
<!doctype html><html lang="sq"><head>
<meta charset="utf-8"><title>{{title}}</title>
<style>body{font-family:system-ui;max-width:900px;margin:40px auto;padding:0 16px}
.card{padding:18px;border:1px solid #e5e7eb;border-radius:14px;box-shadow:0 2px 14px rgba(0,0,0,.04)}
.btn{padding:10px 16px;border-radius:10px;border:1px solid #111827;text-decoration:none}
.btn-primary{background:#111827;color:#fff;border-color:#111827}.btn-ghost{background:#fff;color:#111827}
pre{background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px;overflow:auto}
</style></head><body>
<div class="card">
  <h1>{{title}}</h1>
  <p>Vendos 3 fajllat në <code>{{workdir}}</code>:
     <b>PROMET ARTIKLA.xlsx</b>, <b>PROMET ARTIKLA dd.mm.yyyy.xlsx</b>, <b>FURNITORET.xlsx</b>.</p>
  <form method="POST" action="{{url_for('run_now')}}">
    <button class="btn btn-primary" type="submit">RUN</button>
    <a class="btn btn-ghost" href="{{url_for('download_latest')}}">Latest Export</a>
    <a class="btn btn-ghost" href="{{url_for('health')}}">Health</a>
    <a class="btn btn-ghost" href="{{url_for('logs')}}">Logs</a>
  </form>
  <p><b>OB_OUTDIR:</b> {{outdir}}</p>
  {% if info %}
  <h3>Inputet në work/</h3>
  <pre>{{info}}</pre>
  {% endif %}
  {% if error %}
  <h3 style="color:#b91c1c">ERROR</h3>
  <pre>{{error}}</pre>
  {% endif %}
</div></body></html>
'''

app = Flask(__name__)

def list_work():
    lines = []
    try:
        for f in sorted(os.listdir(WORKDIR)):
            p = os.path.join(WORKDIR, f)
            sz = os.path.getsize(p)
            lines.append(f"{f}  ({sz:,} bytes)")
    except FileNotFoundError:
        lines.append("work/ nuk ekziston")
    return "\n".join(lines) if lines else "(bosh)"

def _latest_export():
    newest, newest_mtime = None, -1
    for root, _, files in os.walk(OUTDIR):
        for f in files:
            if f.lower().endswith(".xlsx"):
                fp = os.path.join(root, f)
                mt = os.path.getmtime(fp)
                if mt > newest_mtime:
                    newest_mtime, newest = mt, fp
    return newest

def log(msg):
    try:
        with open(LOGFILE, "a", encoding="utf-8") as fh:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def has_promet_with_date():
    for f in os.listdir(WORKDIR):
        if f.lower().startswith("promet artikla") and f.lower().endswith(".xlsx") and f.lower() != "promet artikla.xlsx":
            return True
    return False

@app.get("/")
def home():
    return render_template_string(TPL, title=APP_TITLE, workdir=WORKDIR, outdir=OUTDIR, info=list_work())

@app.get("/health")
def health():
    ok = os.path.isdir(WORKDIR) and os.path.isdir(OUTDIR)
    content = f"WORKDIR: {WORKDIR}\nOUTDIR: {OUTDIR}\nOK: {ok}\nFiles in work:\n" + list_work()
    return Response(content, mimetype="text/plain")

@app.get("/logs")
def logs():
    if not os.path.exists(LOGFILE):
        return Response("(no logs yet)", mimetype="text/plain")
    with open(LOGFILE, "r", encoding="utf-8", errors="replace") as fh:
        data = fh.read()
    return Response(data, mimetype="text/plain")

@app.post("/run")
def run_now():
    info = list_work()
    missing = []
    must = ["PROMET ARTIKLA.xlsx", "FURNITORET.xlsx"]
    exists = {f.lower(): True for f in os.listdir(WORKDIR)} if os.path.isdir(WORKDIR) else {}
    for name in must:
        if name.lower() not in exists:
            missing.append(name)
    if not has_promet_with_date():
        missing.append("PROMET ARTIKLA dd.mm.yyyy.xlsx (variant me date)")
    if missing:
        msg = "Mungojnë inputet:\n- " + "\n- ".join(missing) + "\n\nLista aktuale në work/:\n" + info
        log(f"RUN blocked – missing files: {missing}")
        return render_template_string(TPL, title=APP_TITLE, workdir=WORKDIR, outdir=OUTDIR, info=info, error=msg), 400

    try:
        cwd = os.getcwd()
        os.chdir(WORKDIR)
        log("RUN start")
        order_brain.main()
        log("RUN ok")
    except SystemExit as se:
        tb = f"SystemExit: {se}\n\nLista në work/:\n{info}"
        log(f"RUN SystemExit: {se}")
        return render_template_string(TPL, title=APP_TITLE, workdir=WORKDIR, outdir=OUTDIR, info=info, error=tb), 500
    except Exception:
        buf = io.StringIO()
        traceback.print_exc(file=buf)
        tb = buf.getvalue()
        log("RUN exception:\n" + tb)
        return render_template_string(TPL, title=APP_TITLE, workdir=WORKDIR, outdir=OUTDIR, info=info, error=tb), 500
    finally:
        os.chdir(cwd)

    return redirect(url_for("download_latest"))

@app.get("/download")
def download_latest():
    fp = _latest_export()
    if not fp:
        return render_template_string(TPL, title=APP_TITLE, workdir=WORKDIR, outdir=OUTDIR, info=list_work(), error="S'ka ende eksport. Shtyp RUN."), 404
    return send_file(fp, as_attachment=True, download_name=os.path.basename(fp))
