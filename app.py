from flask import Flask, request, jsonify, render_template_string
import time
import os
import json
from pathlib import Path

app = Flask(__name__)

# เก็บข้อมูลผู้ใช้ในหน่วยความจำ
data_storage = {}
TIMEOUT = 10
DATA_FILE = "diamond_data.json"

# โหลดข้อมูลเก่า (ถ้ามี)
def load_data():
    global data_storage
    if Path(DATA_FILE).exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data_storage = json.load(f)
            print(f"[LOADED] {len(data_storage)} accounts from {DATA_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to load data: {e}")
            data_storage = {}

# บันทึกข้อมูล
def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_storage, f, ensure_ascii=False, indent=2)
        print(f"[SAVED] {len(data_storage)} accounts to {DATA_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save data: {e}")

# เรียกใช้ตอนเริ่มต้น
load_data()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diamond Monitor</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { 
            margin: 0; 
            padding: 0;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .fade-in {
            animation: fadeIn 0.3s ease-out;
        }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect } = React;

        const DiamondMonitor = () => {
            const [users, setUsers] = useState({});
            const [connectionStatus, setConnectionStatus] = useState('connecting');
            const [lastUpdate, setLastUpdate] = useState('');
            const [stats, setStats] = useState({
                total: 0,
                online: 0,
                offline: 0,
                diamonds: 0
            });
            const [deviceStats, setDeviceStats] = useState({});
            const [showDeleteModal, setShowDeleteModal] = useState(false);
            const [deleteTarget, setDeleteTarget] = useState(null);

            const STATUS_TIMEOUT = 10000;

            useEffect(() => {
                const fetchInterval = setInterval(fetchData, 2000);
                const updateInterval = setInterval(updateTimeAndStatus, 1000);
                
                fetchData();
                
                return () => {
                    clearInterval(fetchInterval);
                    clearInterval(updateInterval);
                };
            }, []);

            const fetchData = async () => {
                try {
                    const response = await fetch('/get_data');
                    const dataList = await response.json();
                    
                    const now = Date.now();
                    setLastUpdate(new Date().toLocaleTimeString('th-TH'));
                    setConnectionStatus('connected');
                    
                    setUsers(prevUsers => {
                        const updatedUsers = { ...prevUsers };
                        
                        dataList.forEach(data => {
                            const username = data.username || 'Unknown';
                            const diamonds = formatDiamonds(data.diamonds);
                            const device = data.device || 'Unknown';

                            if (!updatedUsers[username]) {
                                updatedUsers[username] = {
                                    username,
                                    diamonds,
                                    device,
                                    startTime: now,
                                    lastUpdate: now,
                                    status: 'ONLINE'
                                };
                            } else {
                                updatedUsers[username] = {
                                    ...updatedUsers[username],
                                    diamonds,
                                    device,
                                    lastUpdate: now
                                };
                            }
                        });
                        
                        return updatedUsers;
                    });
                    
                } catch (error) {
                    setConnectionStatus('error');
                    console.error('Connection error:', error);
                }
            };

            const formatDiamonds = (diamonds) => {
                if (typeof diamonds === 'object' && diamonds !== null) {
                    return Object.entries(diamonds)
                        .map(([k, v]) => `${k}=${v}`)
                        .join(', ');
                }
                return String(diamonds || 0);
            };

            const updateTimeAndStatus = () => {
                const now = Date.now();
                
                setUsers(prevUsers => {
                    const updated = { ...prevUsers };
                    let online = 0;
                    let offline = 0;
                    let totalDiamonds = 0;
                    const devStats = {};
                    
                    Object.keys(updated).forEach(username => {
                        const user = updated[username];
                        const timeSinceUpdate = now - user.lastUpdate;
                        const isOnline = timeSinceUpdate <= STATUS_TIMEOUT;
                        
                        updated[username] = {
                            ...user,
                            status: isOnline ? 'ONLINE' : 'OFFLINE'
                        };
                        
                        if (isOnline) {
                            online++;
                        } else {
                            offline++;
                        }
                        
                        // คำนวณ diamonds
                        let userDiamonds = 0;
                        try {
                            const diamondStr = user.diamonds;
                            if (/^\\d+$/.test(diamondStr)) {
                                userDiamonds = parseInt(diamondStr);
                            } else if (diamondStr.includes('=')) {
                                diamondStr.split(',').forEach(pair => {
                                    const match = pair.match(/=(\\d+)/);
                                    if (match) userDiamonds += parseInt(match[1]);
                                });
                            }
                        } catch (e) {}
                        
                        totalDiamonds += userDiamonds;
                        
                        // สรุปตาม Device
                        const device = user.device || 'Unknown';
                        if (!devStats[device]) {
                            devStats[device] = {
                                total: 0,
                                online: 0,
                                diamonds: 0
                            };
                        }
                        devStats[device].total++;
                        if (isOnline) devStats[device].online++;
                        devStats[device].diamonds += userDiamonds;
                    });
                    
                    setStats({
                        total: Object.keys(updated).length,
                        online,
                        offline,
                        diamonds: totalDiamonds
                    });
                    
                    setDeviceStats(devStats);
                    
                    return updated;
                });
            };

            const handleDeleteUser = async (username) => {
                if (!confirm(`ต้องการลบ ${username} ใช่หรือไม่?`)) return;
                
                try {
                    const response = await fetch('/delete_user', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username })
                    });
                    
                    if (response.ok) {
                        setUsers(prev => {
                            const updated = { ...prev };
                            delete updated[username];
                            return updated;
                        });
                        alert('ลบสำเร็จ!');
                    }
                } catch (error) {
                    alert('เกิดข้อผิดพลาด: ' + error.message);
                }
            };

            const handleDeleteAll = async () => {
                if (!confirm('⚠️ ต้องการลบข้อมูลทั้งหมดใช่หรือไม่?')) return;
                
                try {
                    const response = await fetch('/delete_all', {
                        method: 'POST'
                    });
                    
                    if (response.ok) {
                        setUsers({});
                        alert('ลบข้อมูลทั้งหมดแล้ว!');
                    }
                } catch (error) {
                    alert('เกิดข้อผิดพลาด: ' + error.message);
                }
            };

            const StatCard = ({ title, value, gradient }) => (
                <div className={`relative overflow-hidden rounded-2xl p-6 ${gradient} backdrop-blur-sm`}>
                    <div className="relative z-10">
                        <div className="text-sm font-medium text-white/70 uppercase tracking-wider mb-2">
                            {title}
                        </div>
                        <div className="text-4xl font-bold text-white">
                            {value.toLocaleString()}
                        </div>
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent"></div>
                </div>
            );

            const DeviceCard = ({ device, data }) => (
                <div className="bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-xl p-4 backdrop-blur-sm">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-lg font-bold text-white">{device}</h3>
                        <div className="text-xs px-2 py-1 bg-indigo-500/30 rounded-full text-indigo-200">
                            {data.online}/{data.total}
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Online:</span>
                            <span className="text-emerald-400 font-semibold">{data.online}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Total:</span>
                            <span className="text-slate-300 font-semibold">{data.total}</span>
                        </div>
                        <div className="flex justify-between text-sm pt-2 border-t border-indigo-500/30">
                            <span className="text-slate-400">Diamonds:</span>
                            <span className="text-cyan-400 font-bold">{data.diamonds.toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            );

            return (
                <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
                    <div className="max-w-7xl mx-auto">
                        <div className="mb-8 fade-in">
                            <div className="flex items-center justify-between mb-6">
                                <div>
                                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-2 tracking-tight">
                                        Diamond Monitor
                                    </h1>
                                    <p className="text-slate-400 text-sm md:text-base">Real-time monitoring dashboard</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={handleDeleteAll}
                                        className="px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/50 text-rose-400 rounded-lg text-sm font-medium transition-all duration-200"
                                    >
                                        🗑️ Delete All
                                    </button>
                                    <div className={`hidden md:flex items-center gap-2 px-4 py-2 rounded-full ${
                                        connectionStatus === 'connected'
                                            ? 'bg-emerald-500/20 text-emerald-400'
                                            : connectionStatus === 'error'
                                            ? 'bg-rose-500/20 text-rose-400'
                                            : 'bg-slate-700/50 text-slate-400'
                                    }`}>
                                        <div className={`w-2 h-2 rounded-full ${
                                            connectionStatus === 'connected' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-400'
                                        }`}></div>
                                        <span className="text-sm font-medium">
                                            {connectionStatus === 'connected' ? 'Connected' : 
                                             connectionStatus === 'error' ? 'Error' : 'Connecting'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6 fade-in">
                            <StatCard
                                title="Total Accounts"
                                value={stats.total}
                                gradient="bg-gradient-to-br from-violet-600/20 to-purple-600/20 border border-violet-500/30"
                            />
                            <StatCard
                                title="Online"
                                value={stats.online}
                                gradient="bg-gradient-to-br from-emerald-600/20 to-teal-600/20 border border-emerald-500/30"
                            />
                            <StatCard
                                title="Offline"
                                value={stats.offline}
                                gradient="bg-gradient-to-br from-rose-600/20 to-pink-600/20 border border-rose-500/30"
                            />
                            <StatCard
                                title="Total Diamonds"
                                value={stats.diamonds}
                                gradient="bg-gradient-to-br from-cyan-600/20 to-blue-600/20 border border-cyan-500/30"
                            />
                        </div>

                        {Object.keys(deviceStats).length > 0 && (
                            <div className="mb-8 fade-in">
                                <h2 className="text-2xl font-bold text-white mb-4">Device Summary</h2>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                    {Object.entries(deviceStats)
                                        .sort(([a], [b]) => a.localeCompare(b))
                                        .map(([device, data]) => (
                                            <DeviceCard key={device} device={device} data={data} />
                                        ))}
                                </div>
                            </div>
                        )}

                        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl overflow-hidden border border-slate-700/50 shadow-2xl fade-in">
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="bg-slate-800/80 border-b border-slate-700/50">
                                            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Status
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Device
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Username
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Diamonds
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Object.values(users).length === 0 ? (
                                            <tr>
                                                <td colSpan="5" className="px-6 py-16 text-center">
                                                    <div className="flex flex-col items-center gap-4">
                                                        <div className="w-16 h-16 border-4 border-slate-700 border-t-cyan-500 rounded-full animate-spin"></div>
                                                        <span className="text-slate-500 text-sm font-medium">Waiting for data...</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ) : (
                                            Object.values(users).map((user) => (
                                                <tr 
                                                    key={user.username}
                                                    className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-all duration-200"
                                                >
                                                    <td className="px-6 py-4">
                                                        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
                                                            user.status === 'ONLINE' 
                                                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                                                                : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                                        }`}>
                                                            <div className={`w-1.5 h-1.5 rounded-full ${
                                                                user.status === 'ONLINE' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                                                            }`}></div>
                                                            {user.status}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="text-slate-300 font-medium text-sm">
                                                            {user.device || "Unknown"}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="text-white font-medium text-sm">
                                                            {user.username}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <div className="text-cyan-400 font-bold text-sm">
                                                            {user.diamonds}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <button
                                                            onClick={() => handleDeleteUser(user.username)}
                                                            className="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/50 text-rose-400 rounded-lg text-xs font-medium transition-all duration-200"
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className="mt-6 text-center">
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 text-xs font-medium">
                                <span>Last updated: {lastUpdate || '--:--:--'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            );
        };

        ReactDOM.render(<DiamondMonitor />, document.getElementById('root'));
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/send_data", methods=["POST"])
def receive_data():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON received"}), 400
        
        username = data.get("username", "Unknown")
        diamonds = data.get("diamonds", 0)
        device = data.get("device", "Unknown")

        data_storage[username] = {
            "diamonds": diamonds,
            "device": device,
            "timestamp": time.time()
        }

        # บันทึกทุกครั้งที่มีข้อมูลใหม่
        save_data()

        print(f"[UPDATE] {username} ({device}): {diamonds}")
        return jsonify({"status": "success", "message": "Data received!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_data", methods=["GET"])
def get_data():
    now = time.time()

    # ลบผู้ใช้ที่หมดเวลา (offline)
    expired_users = [user for user, info in data_storage.items() if now - info["timestamp"] > TIMEOUT]
    for user in expired_users:
        print(f"[OFFLINE] Removed {user} (timeout)")
        del data_storage[user]

    result = []
    for user, info in data_storage.items():
        result.append({
            "username": user,
            "diamonds": info["diamonds"],
            "device": info.get("device", "Unknown"),
            "status": "ONLINE"
        })

    return jsonify(result)

@app.route("/delete_user", methods=["POST"])
def delete_user():
    try:
        data = request.json
        username = data.get("username")
        
        if username in data_storage:
            del data_storage[username]
            save_data()
            print(f"[DELETED] User: {username}")
            return jsonify({"status": "success", "message": f"Deleted {username}"})
        else:
            return jsonify({"status": "error", "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete_all", methods=["POST"])
def delete_all():
    try:
        data_storage.clear()
        save_data()
        print("[DELETED] All data cleared")
        return jsonify({"status": "success", "message": "All data deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
