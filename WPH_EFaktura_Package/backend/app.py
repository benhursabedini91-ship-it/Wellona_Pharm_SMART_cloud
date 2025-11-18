import os, sys, traceback, io, datetime, subprocess
# ---- FORCE UTF-8 for all prints/logs (fix UnicodeEncodeError) ----
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from flask import Flask, send_file, render_template_string, redirect, url_for, Response, request
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault("OB_OUTDIR", r"C:\Wellona\wphAI\out\orders")
import order_brain

APP_TITLE = "Wellona Order Brain – Mini UI"
OUTDIR = os.environ.get("OB_OUTDIR", r"C:\Wellona\wphAI\out\orders")
WORKDIR = os.path.join(os.path.dirname(__file__), "work")
LOGDIR = r"C:\Wellona\wphAI\logs"
LOGFILE = os.path.join(LOGDIR, "ui_waitress.log")
INDIR = r"C:\Wellona\wphAI\in"

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
    <a class="btn btn-ghost" href="{{url_for('import_page')}}">Import XML</a>
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
</div>
</body></html>
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

def list_xmls():
    xmls = []
    if os.path.isdir(INDIR):
        for root, _, files in os.walk(INDIR):
            for f in files:
                if f.lower().endswith('.xml'):
                    fp = os.path.join(root, f)
                    rel = os.path.relpath(fp, INDIR)
                    sz = os.path.getsize(fp)
                    mt = os.path.getmtime(fp)
                    dt = datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M')
                    xmls.append((rel, fp, sz, dt))
    return xmls

@app.get("/import")
def import_page():
    xmls = list_xmls()
    if not xmls:
        return render_template_string(TPL, title="Import XML - " + APP_TITLE, workdir=WORKDIR, outdir=OUTDIR, info=list_work(), error="Nuk ka XML në in/."), 404
    
    # Build HTML for list
    html = '<h2>Lista e XML-ve për Import</h2><table border="1"><tr><th>Fajll</th><th>Madhësi</th><th>Modifikuar</th><th>Veprim</th></tr>'
    for rel, fp, sz, dt in xmls:
        html += f'<tr><td>{rel}</td><td>{sz:,} bytes</td><td>{dt}</td><td>'
        html += f'<form method="POST" action="{{url_for("api_import_sopharma")}}" style="display:inline;">'
        html += f'<input type="hidden" name="xml_path" value="{fp}">'
        html += f'<input type="hidden" name="dry_run" value="false">'
        html += f'<button type="submit">Import</button></form> '
        html += f'<form method="POST" action="{{url_for("api_import_sopharma")}}" style="display:inline;">'
        html += f'<input type="hidden" name="xml_path" value="{fp}">'
        html += f'<input type="hidden" name="dry_run" value="true">'
        html += f'<button type="submit">Dry-run</button></form>'
        html += '</td></tr>'
    html += '</table>'
    
    full_tpl = TPL.replace('<div class="card">', '<div class="card">' + html, 1)
    return render_template_string(full_tpl, title="Import XML - " + APP_TITLE, workdir=WORKDIR, outdir=OUTDIR, info=list_work())

@app.post("/api/import/sopharma")
def api_import_sopharma():
    if 'xml_path' in request.form:
        temp_path = request.form['xml_path']
        filename = os.path.basename(temp_path)
    elif 'xml_file' in request.files:
        file = request.files['xml_file']
        if file.filename == '' or not file.filename.lower().endswith('.xml'):
            return {"error": "Fajlli duhet të jetë XML."}, 400
        # Save to temp
        temp_path = os.path.join(WORKDIR, f"temp_import_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")
        file.save(temp_path)
        filename = file.filename
    else:
        return {"error": "Nuk u zgjodh fajll XML ose path."}, 400
    
    dry_run = request.form.get('dry_run', 'true').lower() == 'true'
    
    # Prepare command
    cmd = [sys.executable, 'sopharma_to_erp.py', temp_path]
    if dry_run:
        cmd.append('--dry-run')
    
    # Set env
    env = os.environ.copy()
    env['WPH_USE_FDW'] = '1'
    env['WPH_DB_NAME'] = 'wph_ai'
    env['WPH_DB_HOST'] = '127.0.0.1'
    env['WPH_DB_PASS'] = '0262000'
    
    try:
        log(f"API IMPORT start: {filename}, dry_run={dry_run}")
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__), env=env, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        log(f"API IMPORT result: exit_code={result.returncode}")
        if result.returncode == 0:
            return {"status": "success", "output": output, "dry_run": dry_run}
        else:
            return {"status": "error", "output": output, "exit_code": result.returncode}, 500
    except Exception as e:
        log(f"API IMPORT exception: {e}")
        return {"status": "exception", "error": str(e)}, 500
    finally:
        # Clean temp file only if uploaded
        if 'xml_file' in request.files:
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8055, debug=True)
