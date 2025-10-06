from flask import Flask, request, jsonify, render_template_string
import time
import os

app = Flask(__name__)

# เก็บข้อมูลผู้ใช้ในหน่วยความจำ
data_storage = {}
TIMEOUT = 10

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
        body { margin: 0; padding: 0; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .animate-pulse {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
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
                            
                            if (!updatedUsers[username]) {
                                updatedUsers[username] = {
                                    username,
                                    diamonds,
                                    startTime: now,
                                    lastUpdate: now,
                                    status: 'ONLINE'
                                };
                            } else {
                                updatedUsers[username] = {
                                    ...updatedUsers[username],
                                    diamonds,
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
                    
                    Object.keys(updated).forEach(username => {
                        const user = updated[username];
                        const timeSinceUpdate = now - user.lastUpdate;
                        const isOnline = timeSinceUpdate <= STATUS_TIMEOUT;
                        
                        updated[username] = {
                            ...user,
                            status: isOnline ? 'ONLINE' : 'OFFLINE',
                            elapsedTime: Math.floor((now - user.startTime) / 1000)
                        };
                        
                        if (isOnline) {
                            online++;
                        } else {
                            offline++;
                        }
                        
                        try {
                            const diamondStr = user.diamonds;
                            if (/^\d+$/.test(diamondStr)) {
                                totalDiamonds += parseInt(diamondStr);
                            } else if (diamondStr.includes('=')) {
                                diamondStr.split(',').forEach(pair => {
                                    const match = pair.match(/=(\d+)/);
                                    if (match) totalDiamonds += parseInt(match[1]);
                                });
                            }
                        } catch (e) {}
                    });
                    
                    setStats({
                        total: Object.keys(updated).length,
                        online,
                        offline,
                        diamonds: totalDiamonds
                    });
                    
                    return updated;
                });
            };

            const formatTime = (seconds) => {
                if (!seconds) return '0s';
                if (seconds < 60) return `${seconds}s`;
                if (seconds < 3600) {
                    const mins = Math.floor(seconds / 60);
                    const secs = seconds % 60;
                    return `${mins}m ${secs}s`;
                }
                const hours = Math.floor(seconds / 3600);
                const mins = Math.floor((seconds % 3600) / 60);
                return `${hours}h ${mins}m`;
            };

            const StatCard = ({ icon, title, value, color, borderColor }) => (
                <div className={`bg-zinc-900 rounded-xl p-6 border-2 ${borderColor} flex-1 min-w-0 backdrop-blur-sm bg-opacity-50`}>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-zinc-400 text-sm font-medium uppercase tracking-wider">
                            {title}
                        </span>
                        <span className="text-2xl">{icon}</span>
                    </div>
                    <div className={`text-4xl font-bold ${color}`}>
                        {value.toLocaleString()}
                    </div>
                </div>
            );

            return (
                <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 p-6">
                    <div className="max-w-7xl mx-auto">
                        <div className="mb-8">
                            <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                                <span className="text-4xl">💎</span>
                                Diamond Monitor
                            </h1>
                            <p className="text-zinc-400">Real-time monitoring dashboard</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                            <StatCard
                                icon="👥"
                                title="Accounts"
                                value={stats.total}
                                color="text-purple-500"
                                borderColor="border-purple-500"
                            />
                            <StatCard
                                icon="✅"
                                title="Online"
                                value={stats.online}
                                color="text-green-400"
                                borderColor="border-green-400"
                            />
                            <StatCard
                                icon="❌"
                                title="Offline"
                                value={stats.offline}
                                color="text-red-400"
                                borderColor="border-red-400"
                            />
                            <StatCard
                                icon="💎"
                                title="Diamonds"
                                value={stats.diamonds}
                                color="text-blue-400"
                                borderColor="border-blue-400"
                            />
                        </div>

                        <div className="bg-zinc-900 rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="bg-zinc-800 border-b-2 border-zinc-700">
                                            <th className="px-6 py-4 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider">
                                                Status
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider">
                                                User
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider">
                                                Time
                                            </th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider">
                                                Diamonds
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-zinc-800">
                                        {Object.values(users).length === 0 ? (
                                            <tr>
                                                <td colSpan="4" className="px-6 py-12 text-center text-zinc-500">
                                                    <div className="flex flex-col items-center gap-2">
                                                        <span className="text-4xl animate-pulse">📡</span>
                                                        <span>Waiting for data...</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ) : (
                                            Object.values(users).map((user) => (
                                                <tr 
                                                    key={user.username}
                                                    className="hover:bg-zinc-800 transition-colors duration-150"
                                                >
                                                    <td className="px-6 py-4">
                                                        <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${
                                                            user.status === 'ONLINE' 
                                                                ? 'bg-green-500 bg-opacity-20 text-green-400' 
                                                                : 'bg-red-500 bg-opacity-20 text-red-400'
                                                        }`}>
                                                            <span className={`w-2 h-2 rounded-full ${
                                                                user.status === 'ONLINE' ? 'bg-green-400' : 'bg-red-400'
                                                            } ${user.status === 'ONLINE' ? 'animate-pulse' : ''}`}></span>
                                                            {user.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-4 text-white font-medium">
                                                        {user.username}
                                                    </td>
                                                    <td className="px-6 py-4 text-zinc-400 font-mono">
                                                        {formatTime(user.elapsedTime)}
                                                    </td>
                                                    <td className="px-6 py-4 text-yellow-400 font-bold">
                                                        {user.diamonds}
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className={`mt-6 px-6 py-4 rounded-xl text-center text-sm font-medium transition-all duration-300 ${
                            connectionStatus === 'connected'
                                ? 'bg-green-950 bg-opacity-50 text-green-400 border border-green-800'
                                : connectionStatus === 'error'
                                ? 'bg-red-950 bg-opacity-50 text-red-400 border border-red-800'
                                : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                        }`}>
                            {connectionStatus === 'connected' ? (
                                <span className="flex items-center justify-center gap-2">
                                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                                    Connected • Last updated: {lastUpdate}
                                </span>
                            ) : connectionStatus === 'error' ? (
                                'Connection error - Retrying...'
                            ) : (
                                'Connecting to server...'
                            )}
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
