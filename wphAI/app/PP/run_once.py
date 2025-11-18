import os, sys, pathlib
# UTF-8 për stdout/stderr
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
# ENV & CWD
os.environ["OB_OUTDIR"] = r"C:\Wellona\wphAI\out\orders"
os.chdir(r"C:\Wellona\wphAI\app\work")
sys.path.append(r"C:\Wellona\wphAI\app")
import order_brain
order_brain.main()
