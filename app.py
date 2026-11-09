from flask import Flask, request, jsonify
import sqlite3
import secrets
import datetime
import os

app = Flask(__name__)
DB_PATH = "license.db"
ADMIN_SECRET = "FLEEX_ADMIN_2026" # این رمز رو عوض کن!

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            hwid TEXT,
            expires TEXT,
            active INTEGER DEFAULT 1
        )""")

@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.json or {}
    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify({"status": "error", "message": "Missing data"}), 400

    with sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT hwid, expires, active FROM licenses WHERE key=?", (key,)).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Invalid license"}), 401
            
        db_hwid, expires, active = row
        
        if active == 0:
            return jsonify({"status": "error", "message": "License disabled"}), 403
            
        if expires and datetime.datetime.now() > datetime.datetime.strptime(expires, "%Y-%m-%d"):
            return jsonify({"status": "error", "message": "License expired"}), 403

        if db_hwid is None:
            c.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
            c.commit()
        elif db_hwid != hwid:
            return jsonify({"status": "error", "message": "Locked to another device"}), 403
            
    return jsonify({"status": "success"}), 200

@app.route('/admin/gen')
def gen():
    if request.args.get("secret") != ADMIN_SECRET:
        return "Unauthorized", 401
        
    days = int(request.args.get("days", 30))
    new_key = f"FLEEX-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO licenses (key, expires) VALUES (?, ?)", (new_key, exp_date))
        c.commit()
        
    return jsonify({"key": new_key, "expires": exp_date})

if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get("SERVER_PORT", 5000)))
