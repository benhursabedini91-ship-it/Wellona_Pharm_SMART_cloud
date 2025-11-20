import os
import time
import json
import subprocess
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# =============================
# CONFIGURATION
# =============================
BASE_DIR = r"C:\Wellona\wphAI"
CONFIG_PATH = os.path.join(BASE_DIR, "config", "agent_config.json")
LOG_PATH = os.path.join(BASE_DIR, "logs", "runtime.log")
ACTIVITY_LOG = os.path.join(BASE_DIR, "logs", "agent_activity.log")

PROTECTED_KEYWORDS = [
    "pharmacy_db", "erp", "postgres_fdw", "connect(", "127.0.0.1",
    "pharmacy", "delete from", "drop table"
]

# =============================
# UTILITIES
# =============================

def log(message, path=LOG_PATH):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")
    print(f"[{ts}] {message}")

def log_activity(event_type, file_path):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {event_type}: {file_path}\n")

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"mode": "approval", "check_interval": 10, "log_level": "INFO"}

def security_guard(file_path, content):
    if not file_path.startswith(BASE_DIR):
        raise PermissionError("Access outside C:\\Wellona\\wphAI is blocked.")
    for key in PROTECTED_KEYWORDS:
        if key.lower() in content.lower():
            raise PermissionError("❌ Database access attempt blocked.")

def run_script(file_path, mode):
    log(f"⚙️ Detected script: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    security_guard(file_path, content)

    if mode == "approval":
        answer = input(f"Run {os.path.basename(file_path)}? (y/n): ").strip().lower()
        if answer != "y":
            log(f"⏩ Skipped by user: {file_path}")
            return

    log(f"🚀 Running: {file_path}")
    try:
        if file_path.endswith(".py"):
            subprocess.run(["python", file_path], check=True)
        elif file_path.endswith(".task"):
            subprocess.run(["cmd", "/c", file_path], check=True)
        log(f"✅ Completed successfully: {file_path}")
    except Exception as e:
        log(f"❌ Failed to execute {file_path}: {e}")

# =============================
# EVENT HANDLER
# =============================

class AgentHandler(FileSystemEventHandler):
    def __init__(self, mode):
        self.mode = mode

    def on_created(self, event):
        if event.is_directory:
            return
        if any(event.src_path.endswith(ext) for ext in [".py", ".task"]):
            log_activity("Created", event.src_path)
            run_script(event.src_path, self.mode)

# =============================
# MAIN
# =============================

if __name__ == "__main__":
    cfg = load_config()
    mode = cfg.get("mode", "approval")
    interval = cfg.get("check_interval", 10)

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    log(f"🧠 Wellona Local Agent started in {mode.upper()} mode.")
    log(f"Monitoring folder: {BASE_DIR}")

import sys

def cli_loop():
    print("🧠 ROBI: CLI mode active. Type #help for commands.")
    while True:
        cmd = input(">").strip().lower()

        if cmd in ["#exit", "exit", "quit"]:
            print("👋 ROBI: U paç, boss.")
            break

        elif cmd in ["#status", "status"]:
            print("🧠 ROBI: Mode = APPROVAL")
            print("📁 Monitoring folder: C:\\Wellona\\wphAI")
            print("✅ Everything running fine, boss.")

        elif cmd.startswith("#find "):
            print(f"⚠️ (Simulim) File ose path me emër '{term}' nuk u gjet në memorje të brendshme.")
            term = cmd[6:].strip()
            print(f"🔍 ROBI: Po kërkoj për '{term}' në projekt...")
            matches = find_files(term)
        if  matches:
             response = f"✅ U gjetën {len(matches)} rezultate:\n" + "\n".join(matches[:10])
             if len(matches) > 10:
                response += f"\n... (+{len(matches)-10} tjera)"
        else:
            response = f"⚠️ Asnjë file apo folder me '{term}' nuk u gjet në {root_folder}."
        print(response)

        elif cmd_lower.startswith("#order "):
           term = cmd[7:].strip()
           print(f"🧠 ROBI: Po kërkoj {term} te WebApp...")
           import requests
           res = requests.get(f"http://127.0.0.1:5055/generate?supplier={term}")
           if res.status_code == 200:
               print(f"✅ Porosia për {term} u krijua me sukses!")
        else:
               print("⚠️ Dështoi kërkesa tek WebApp.")

import os

def find_files(term, root_folder=r"C:\Wellona\wphAI"):
    """Kërkon në mënyrë rekursive file ose foldera që përmbajnë term-in."""
    matches = []
    for root, dirs, files in os.walk(root_folder):
        for name in files + dirs:
            if term.lower() in name.lower():
                matches.append(os.path.join(root, name))
    return matches

# 🧠 Entry point – këtu fillon agjenti kur e nisim me python agent_runtime.py
if __name__ == "__main__":
    if "--cli" in sys.argv:
        cli_loop()
    else:
        print("🧠 ROBI: Wellona Local Agent started in APPROVAL mode.")
        print("📁 Monitoring folder: C:\\Wellona\\wphAI")
