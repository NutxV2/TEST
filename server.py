from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# เก็บข้อมูลผู้ใช้ในหน่วยความจำ
# โครงสร้าง: { "username": {"diamonds": 123, "timestamp": 1728181818.123} }
data_storage = {}

# ระยะเวลาที่จะถือว่า user offline (หน่วยเป็นวินาที)
TIMEOUT = 10


@app.route("/")
def index():
    return "Server Running!"


@app.route("/send_data", methods=["POST"])
def receive_data():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON received"}), 400

        username = data.get("username", "Unknown")
        diamonds = data.get("diamonds", 0)

        # บันทึกข้อมูลพร้อมเวลาอัปเดตล่าสุด
        data_storage[username] = {
            "diamonds": diamonds,
            "timestamp": time.time()
        }

        print(f"[UPDATE] {username}: {diamonds}")
        return jsonify({"status": "success", "message": "Data received!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/get_data", methods=["GET"])
def get_data():
    now = time.time()

    # ลบผู้ใช้ที่ไม่ได้อัปเดตเกิน TIMEOUT วินาที
    expired_users = [user for user, info in data_storage.items() if now - info["timestamp"] > TIMEOUT]
    for user in expired_users:
        print(f"[OFFLINE] Removed {user} (timeout)")
        del data_storage[user]

    # ส่งข้อมูลเฉพาะ user ที่ยังออนไลน์
    result = []
    for user, info in data_storage.items():
        result.append({
            "username": user,
            "diamonds": info["diamonds"],
            "status": "ONLINE"
        })

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
