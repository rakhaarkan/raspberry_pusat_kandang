import subprocess
import time
import os
import psutil
import requests
from dotenv import load_dotenv
import signal

# ================= CONFIG =================
load_dotenv("config.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH")
LOCAL_PORT = os.getenv("LOCAL_PORT", "5678")
DOMAIN = os.getenv("DOMAIN")  # Contoh: https://rakhafarm.dpdns.org

if not BOT_TOKEN or not WEBHOOK_PATH or not DOMAIN:
    raise RuntimeError("BOT_TOKEN, WEBHOOK_PATH atau DOMAIN missing in config.env")

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
N8N_PID_FILE = os.path.join(STATE_DIR, "n8n_pid.txt")
os.makedirs(STATE_DIR, exist_ok=True)

# ================= UTIL =================
def run(cmd, env=None):
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        preexec_fn=os.setsid
    )

def kill_n8n_if_running():
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["cmdline"] and "n8n" in " ".join(p.info["cmdline"]):
                print(f"Killing old n8n PID {p.pid}")
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            pass

# ================= N8N =================
def start_n8n():
    print("Starting n8n...")
    kill_n8n_if_running()

    env = os.environ.copy()
    env.update({
        "N8N_HOST": "0.0.0.0",
        "N8N_PORT": LOCAL_PORT,
        "N8N_PROTOCOL": "https" if DOMAIN.startswith("https") else "http",
        "WEBHOOK_URL": DOMAIN,
        "N8N_EDITOR_BASE_URL": DOMAIN,
        "N8N_SECURE_COOKIE": "false",
    })

    proc = run(["n8n"], env=env)

    with open(N8N_PID_FILE, "w") as f:
        f.write(str(proc.pid))

    print("✅ n8n started")
    time.sleep(5)

# ================= TELEGRAM =================
def set_telegram_webhook():
    webhook_url = f"{DOMAIN}{WEBHOOK_PATH}"
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo", timeout=5)
        current = r.json().get("result", {}).get("url")
        if current == webhook_url:
            print("Telegram webhook already set correctly")
            return
    except Exception:
        pass

    print("Setting Telegram webhook...")
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": webhook_url},
        timeout=5
    )
    print("Telegram response:", r.json())

# ================= CHECK STATUS =================
def check_status():
    print("\n=== CHECK N8N & CLOUDFLARE SERVICE ===\n")
    
    # Check n8n
    n8n_running = False
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["cmdline"] and "n8n" in " ".join(p.info["cmdline"]):
                print(f"n8n is running (PID: {p.pid})")
                n8n_running = True
                break
        except Exception:
            pass
    if not n8n_running:
        print("n8n not running → starting")
        start_n8n()
    else:
        print("n8n is alive")

    # Cloudflare tunnel: cukup cek service
    import shutil
    if shutil.which("systemctl"):
        import subprocess
        try:
            status = subprocess.run(["systemctl", "is-active", "cloudflared"], capture_output=True, text=True)
            print(f"Cloudflare service status: {status.stdout.strip()}")
        except Exception as e:
            print("Error checking cloudflared service:", e)
    print()

# ================= MAIN =================
def run_n8n():
    start_n8n()
    set_telegram_webhook()
    check_status()
    print(f"\nSTACK READY! Domain: {DOMAIN}")
