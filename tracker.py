import os, sqlite3, requests
from datetime import datetime, timezone
from flask import Flask, request, redirect, jsonify
from user_agents import parse as ua_parse

# ====== 🔧 ตั้งค่าพื้นฐาน (ฝังค่าของพี่ไว้เลย) ======
TELEGRAM_TOKEN = "8231066204:AAF5VV9wRDJzjruYrKq9FIgo-Ee_ieoJPk4"
CHAT_ID = "7205194061"
DEST_URL = "https://angpaoap98.com/"
DB_PATH = "clicks.db"

# ====== 🚀 เริ่มต้นระบบ Flask ======
app = Flask(__name__)

# ====== ฐานข้อมูล local (sqlite) ======
with sqlite3.connect(DB_PATH) as con:
    con.execute("""CREATE TABLE IF NOT EXISTS clicks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT, ip TEXT, ua TEXT, device TEXT, os TEXT, browser TEXT,
        country TEXT, city TEXT, ts TEXT
    )""")

# ====== ฟังก์ชันช่วยเหลือ ======
def client_ip():
    h = request.headers.get("X-Forwarded-For")
    return (h.split(",")[0].strip() if h else request.remote_addr) or "0.0.0.0"

def geo(ip):
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
        j = r.json()
        return j.get("country_name") or "Unknown", j.get("city") or "Unknown"
    except Exception:
        return "Unknown", "Unknown"

def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text},
            timeout=5
        )
    except Exception:
        pass

# ====== หน้า root (เช็กว่าเว็บทำงาน) ======
@app.get("/")
def root():
    return jsonify(ok=True, msg="tracker online", example="/click?ad=test123")

@app.get("/health")
def health():
    return "ok", 200

# ====== ตัวหลัก: ดักคลิก ======
@app.get("/click")
def track_click():
    ad = request.args.get("ad", "default")
    ip = client_ip()
    ua_raw = request.headers.get("User-Agent", "-")[:300]

    ua = ua_parse(ua_raw)
    device = "Mobile" if ua.is_mobile else "Tablet" if ua.is_tablet else "PC" if ua.is_pc else "Other"
    os_name = f"{ua.os.family} {ua.os.version_string}".strip()
    br_name = f"{ua.browser.family} {ua.browser.version_string}".strip()

    country, city = geo(ip)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO clicks(ad,ip,ua,device,os,browser,country,city,ts) VALUES(?,?,?,?,?,?,?,?,?)",
            (ad, ip, ua_raw, device, os_name, br_name, country, city, ts)
        )
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        total_today = con.execute(
            "SELECT COUNT(*) FROM clicks WHERE ts LIKE ?", (f"{today}%",)
        ).fetchone()[0]

    msg = (
        "🔔 มีการคลิกเข้าเซลเพจ\n"
        f"📢 แคมเปญ: {ad}\n"
        f"🌐 IP: {ip}\n"
        f"📍 ที่มา: {city}, {country}\n"
        f"📱 อุปกรณ์: {device}\n"
        f"🖥 OS/Browser: {os_name} / {br_name}\n"
        f"🕒 เวลา: {ts}\n"
        f"📊 รวมวันนี้: {total_today} ครั้ง"
    )
    send_telegram(msg)
    return redirect(DEST_URL, code=302)

# ====== รันเซิร์ฟเวอร์ ======
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
