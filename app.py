from flask import Flask, request, jsonify, render_template_string
import time
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # ✅ ตำแหน่งถูกต้อง ต้องอยู่หลังสร้าง app แล้ว

# เก็บข้อมูลผู้ใช้ในหน่วยความจำ
data_storage = {}
TIMEOUT = 60  # ✅ เพิ่มเวลา timeout เพื่อกันลบเร็วเกินไป

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
        // React Dashboard (เหมือนเดิม)
        const { useState, useEffect } = React;
        const DiamondMonitor = () => {
            const [users, setUsers] = useState({});
            const [connectionStatus, setConnectionStatus] = useState('connecting');
            const [lastUpdate, setLastUpdate] = useState('');
            const [stats, setStats] = useState({ total: 0, online: 0, offline: 0, diamonds: 0 });
            const STATUS_TIMEOUT = 10000;

            useEffect(() => {
                const fetchInterval = setInterval(fetchData, 2000);
                const updateInterval = setInterval(updateTimeAndStatus, 1000);
                fetchData();
                return () => { clearInterval(fetchInterval); clearInterval(updateInterval); };
            }, []);

            const fetchData = async () => {
                try {
                    const response = await fetch('/get_data');
                    const dataList = await response.json();
                    const now = Date.now();
                    setLastUpdate(new Date().toLocaleTimeString('th-TH'));
                    setConnectionStatus('connected');
                    setUsers(prev => {
                        const updated = { ...prev };
                        dataList.forEach(data => {
                            const username = data.username || 'Unknown';
                            const diamonds = formatDiamonds(data.diamonds);
                            updated[username] = {
                                ...updated[username],
                                username,
                                diamonds,
                                lastUpdate: now,
                                startTime: updated[username]?.startTime || now,
                                status: data.status || 'ONLINE'
                            };
                        });
                        return updated;
                    });
                } catch {
                    setConnectionStatus('error');
                }
            };

            const formatDiamonds = (d) => typeof d === 'object' ? 
                Object.entries(d).map(([k,v]) => `${k}=${v}`).join(', ') : String(d || 0);

            const updateTimeAndStatus = () => {
                const now = Date.now();
                setUsers(prev => {
                    const updated = { ...prev };
                    Object.keys(updated).forEach(u => {
                        const user = updated[u];
                        const timeSince = now - user.lastUpdate;
                        updated[u].status = timeSince <= STATUS_TIMEOUT ? 'ONLINE' : 'OFFLINE';
                        updated[u].elapsedTime = Math.floor((now - user.startTime) / 1000);
                    });
                    return updated;
                });
                calculateStats();
            };

            const calculateStats = () => {
                const now = Date.now();
                let online = 0, offline = 0, diamonds = 0;
                Object.values(users).forEach(u => {
                    const t = now - u.lastUpdate;
                    if (t <= STATUS_TIMEOUT) online++; else offline++;
                    const d = u.diamonds;
                    if (/^\\d+$/.test(d)) diamonds += parseInt(d);
                    else if (d.includes('=')) d.split(',').forEach(p => {
                        const m = p.match(/=(\\d+)/); if (m) diamonds += parseInt(m[1]);
                    });
                });
                setStats({ total: Object.keys(users).length, online, offline, diamonds });
            };

            const formatTime = (s) => s < 60 ? `${s}s` :
                s < 3600 ? `${Math.floor(s/60)}m ${s%60}s` :
                `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;

            const StatCard = ({ icon, title, value, color, borderColor }) => (
                <div className={\`bg-zinc-900 rounded-xl p-6 border-2 \${borderColor} flex-1 backdrop-blur-sm\`}>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-zinc-400 text-sm font-medium uppercase tracking-wider">{title}</span>
                        <span className="text-2xl">{icon}</span>
                    </div>
                    <div className={\`text-4xl font-bold \${color}\`}>{value.toLocaleString()}</div>
                </div>
            );

            return (
                <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 p-6">
                    <div className="max-w-7xl mx-auto">
                        <h1 className="text-4xl font-bold text-white mb-4 flex items-center gap-3">💎 Diamond Monitor</h1>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                            <StatCard icon="👥" title="Accounts" value={stats.total} color="text-purple-500" borderColor="border-purple-500" />
                            <StatCard icon="✅" title="Online" value={stats.online} color="text-green-400" borderColor="border-green-400" />
                            <StatCard icon="❌" title="Offline" value={stats.offline} color="text-red-400" borderColor="border-red-400" />
                            <StatCard icon="💎" title="Diamonds" value={stats.diamonds} color="text-blue-400" borderColor="border-blue-400" />
                        </div>
                        <div className="bg-zinc-900 rounded-xl overflow-hidden border border-zinc-800">
                            <table className="w-full">
                                <thead><tr className="bg-zinc-800"><th className="px-6 py-4 text-left text-zinc-400">Status</th><th className="px-6 py-4 text-left text-zinc-400">User</th><th className="px-6 py-4 text-left text-zinc-400">Time</th><th className="px-6 py-4 text-left text-zinc-400">Diamonds</th></tr></thead>
                                <tbody className="divide-y divide-zinc-800">
                                    {Object.values(users).length === 0 ? (
                                        <tr><td colSpan="4" className="px-6 py-12 text-center text-zinc-500">📡 Waiting for data...</td></tr>
                                    ) : Object.values(users).map(u => (
                                        <tr key={u.username} className="hover:bg-zinc-800 transition">
                                            <td className="px-6 py-4">
                                                <span className={\`px-3 py-1 rounded-full text-xs font-bold \${u.status==='ONLINE'?'bg-green-500/20 text-green-400':'bg-red-500/20 text-red-400'}\`}>
                                                    {u.status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-white">{u.username}</td>
                                            <td className="px-6 py-4 text-zinc-400 font-mono">{formatTime(u.elapsedTime)}</td>
                                            <td className="px-6 py-4 text-yellow-400 font-bold">{u.diamonds}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className={\`mt-6 px-6 py-4 rounded-xl text-center text-sm font-medium border transition-all duration-300 \${connectionStatus==='connected'?'bg-green-950 text-green-400 border-green-800':connectionStatus==='error'?'bg-red-950 text-red-400 border-red-800':'bg-zinc-800 text-zinc-400 border-zinc-700'}\`}>
                            {connectionStatus==='connected' ? \`Connected • Last updated: \${lastUpdate}\` : connectionStatus==='error' ? 'Connection error - Retrying...' : 'Connecting to server...'}
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
        data_storage[username] = {"diamonds": diamonds, "timestamp": time.time()}
        print(f"[UPDATE] {username}: {diamonds}")
        return jsonify({"status": "success", "message": "Data received!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_data", methods=["GET"])
def get_data():
    now = time.time()
    result = []
    for user, info in data_storage.items():
        status = "ONLINE" if now - info["timestamp"] <= TIMEOUT else "OFFLINE"
        result.append({
            "username": user,
            "diamonds": info["diamonds"],
            "status": status
        })
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
