from flask import Flask, request, jsonify

app = Flask(__name__)

# เก็บข้อมูลชั่วคราวใน memory
data_storage = []

@app.route("/")
def index():
    return "Server Running!"

@app.route("/send_data", methods=["POST"])
def receive_data():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON received"}), 400
        
        # เพิ่มข้อมูลลง memory
        data_storage.append(data)
        print("Received data:", data)
        return jsonify({"status": "success", "message": "Data received!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_data", methods=["GET"])
def get_data():
    # คืนข้อมูลทั้งหมดที่เก็บไว้ชั่วคราว
    return jsonify(data_storage)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
