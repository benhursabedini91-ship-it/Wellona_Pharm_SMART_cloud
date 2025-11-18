import os, sys
os.environ.setdefault("OB_OUTDIR", r"C:\Wellona\wphAI\out\orders")
sys.path.append(os.path.dirname(__file__))
import order_brain
order_brain.main()
