from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import time
import os
import json
from functools import lru_cache
from datetime import datetime
import gzip
from supabase import create_client

app = Flask(__name__)
CORS(app)

# Configuration
TIMEOUT = 30
CACHE_TTL = 1  # Cache for 1 second

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase URL หรือ Key ไม่ถูกตั้งค่าใน Environment Variables")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Table name in Supabase
TABLE_NAME = "users"

def init_db():
    """
    Create table in Supabase if it doesn't exist.
    Run this SQL in Supabase SQL Editor:
    
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        diamonds TEXT,
        device TEXT,
        timestamp BIGINT
    );
    
    CREATE INDEX IF NOT EXISTS idx_timestamp ON users(timestamp);
    CREATE INDEX IF NOT EXISTS idx_device ON users(device);
    """
    print("📊 Make sure to create the 'users' table in Supabase SQL Editor")
    print("   See init_db() function for SQL commands")

init_db()

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
        .stat-card, .device-card, .user-row {
            will-change: transform;
            transform: translateZ(0);
        }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect, useCallback, useMemo, memo } = React;

        const StatCard = memo(({ title, value, gradient }) => (
            <div className={`stat-card relative overflow-hidden rounded-2xl p-6 ${gradient} backdrop-blur-sm`}>
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
        ));

        const DeviceCard = memo(({ device, data }) => (
            <div className="device-card bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-xl p-4 backdrop-blur-sm">
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
        ));

        const UserRow = memo(({ user, onDelete }) => (
            <tr className="user-row border-b border-slate-800/50 hover:bg-slate-800/30 transition-all duration-200">
                <td className="px-6 py-4 text-center">
                    <div className="flex justify-center items-center">
                        <div
                            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
                                user.status === 'ONLINE'
                                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                    : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            }`}
                        >
                            <div
                                className={`w-1.5 h-1.5 rounded-full ${
                                    user.status === 'ONLINE'
                                        ? 'bg-emerald-400 animate-pulse'
                                        : 'bg-rose-400'
                                }`}
                            ></div>
                            {user.status}
                        </div>
                    </div>
                </td>
                <td className="px-6 py-4">
                    <div className="text-slate-300 font-medium text-center text-sm">
                        {user.device || "Unknown"}
                    </div>
                </td>
                <td className="px-6 py-4">
                    <div className="text-white font-medium text-center text-sm">
                        {user.username}
                    </div>
                </td>
                <td className="px-6 py-4">
                    <div className="text-cyan-400 font-bold text-center text-sm">
                        {user.diamonds}
                    </div>
                </td>
                <td className="px-6 py-4 text-center">
                    <div className="flex justify-center items-center">
                        <button
                            onClick={() => onDelete(user.username)}
                            className="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/50 text-rose-400 rounded-lg text-xs font-medium transition-all duration-200"
                        >
                            Delete
                        </button>
                    </div>
                </td>
            </tr>
        ));

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
            const [isLoading, setIsLoading] = useState(true);
            const [sortConfig, setSortConfig] = useState({ key: 'diamonds', direction: 'desc' });
            const STATUS_TIMEOUT = 30000;

            const fetchData = useCallback(async () => {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);

                try {
                    const response = await fetch('/get_data', {
                        signal: controller.signal,
                        headers: { 'Accept': 'application/json' }
                    });
                    clearTimeout(timeoutId);
                    
                    const dataList = await response.json();
                    const now = Date.now();
                    
                    setLastUpdate(new Date().toLocaleTimeString('th-TH'));
                    setConnectionStatus('connected');
                    setIsLoading(false);
                    
                    setUsers(prevUsers => {
                        const updatedUsers = { ...prevUsers };
                        dataList.forEach(data => {
                            const username = data.username || 'Unknown';
                            const lastUpdate = now - data.last_seen * 1000;
                            
                            updatedUsers[username] = {
                                username,
                                diamonds: formatDiamonds(data.diamonds),
                                device: data.device || 'Unknown',
                                lastUpdate,
                                status: data.status || 'OFFLINE'
                            };
                        });
                        return updatedUsers;
                    });
                    
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        setConnectionStatus('error');
                        console.error('Connection error:', error);
                    }
                } finally {
                    clearTimeout(timeoutId);
                }
            }, []);

            const formatDiamonds = useMemo(() => (diamonds) => {
                try {
                    const parsed = JSON.parse(diamonds);
                    if (typeof parsed === 'object' && parsed !== null) {
                        return Object.entries(parsed)
                            .map(([k, v]) => `${k}=${v}`)
                            .join(', ');
                    }
                    return String(parsed || 0);
                } catch (e) {
                    return String(diamonds || 0);
                }
            }, []);

            const updateTimeAndStatus = useCallback(() => {
                requestAnimationFrame(() => {
                    const now = Date.now();
                    
                    setUsers(prevUsers => {
                        const updated = { ...prevUsers };
                        let online = 0, offline = 0, totalDiamonds = 0;
                        const devStats = {};
                        
                        for (const username in updated) {
                            const user = updated[username];
                            const timeSinceUpdate = now - user.lastUpdate;
                            const isOnline = timeSinceUpdate <= STATUS_TIMEOUT;
                            
                            updated[username] = { ...user, status: isOnline ? 'ONLINE' : 'OFFLINE' };
                            
                            isOnline ? online++ : offline++;
                            
                            let userDiamonds = 0;
                            const diamondStr = user.diamonds;
                            if (/^\d+$/.test(diamondStr)) {
                                userDiamonds = parseInt(diamondStr, 10);
                            } else if (diamondStr.includes('=')) {
                                const matches = diamondStr.matchAll(/=(\d+)/g);
                                for (const match of matches) {
                                    userDiamonds += parseInt(match[1], 10);
                                }
                            }
                            
                            totalDiamonds += userDiamonds;
                            
                            const device = user.device || 'Unknown';
                            if (!devStats[device]) {
                                devStats[device] = { total: 0, online: 0, diamonds: 0 };
                            }
                            devStats[device].total++;
                            if (isOnline) devStats[device].online++;
                            devStats[device].diamonds += userDiamonds;
                        }
                        
                        setStats({
                            total: Object.keys(updated).length,
                            online,
                            offline,
                            diamonds: totalDiamonds
                        });
                        setDeviceStats(devStats);
                        
                        return updated;
                    });
                });
            }, [STATUS_TIMEOUT]);

            const handleDeleteUser = useCallback(async (username) => {
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
                    }
                } catch (error) {
                    alert('เกิดข้อผิดพลาด: ' + error.message);
                }
            }, []);

            const handleDeleteAll = useCallback(async () => {
                if (!confirm('⚠️ ต้องการลบข้อมูลทั้งหมดใช่หรือไม่?')) return;
                
                try {
                    const response = await fetch('/delete_all', { method: 'POST' });
                    if (response.ok) {
                        setUsers({});
                        setDeviceStats({});
                    }
                } catch (error) {
                    alert('เกิดข้อผิดพลาด: ' + error.message);
                }
            }, []);

            const handleCleanupOffline = useCallback(async () => {
                if (!confirm('ต้องการลบข้อมูลที่ออฟไลน์ใช่หรือไม่?')) return;
                
                try {
                    const response = await fetch('/cleanup_offline', { method: 'POST' });
                    if (response.ok) fetchData();
                } catch (error) {
                    alert('เกิดข้อผิดพลาด: ' + error.message);
                }
            }, [fetchData]);

            useEffect(() => {
                const fetchInterval = setInterval(fetchData, 2000);
                const updateInterval = setInterval(updateTimeAndStatus, 1000);
                
                fetchData();
                
                return () => {
                    clearInterval(fetchInterval);
                    clearInterval(updateInterval);
                };
            }, [fetchData, updateTimeAndStatus]);

            const sortedUsers = useMemo(() => {
                const userArray = Object.values(users);

                userArray.sort((a, b) => {
                    if (a.status !== b.status) {
                        return a.status === 'ONLINE' ? -1 : 1;
                    }

                    if (sortConfig.key === 'diamonds') {
                        const parseDiamonds = (d) => {
                            let total = 0;
                            if (/^\d+$/.test(d)) total = parseInt(d, 10);
                            else if (d.includes('=')) {
                                const matches = d.matchAll(/=(\d+)/g);
                                for (const match of matches) total += parseInt(match[1], 10);
                            }
                            return total;
                        };
                        const aVal = parseDiamonds(a.diamonds);
                        const bVal = parseDiamonds(b.diamonds);
                        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
                    }

                    return a.username.localeCompare(b.username);
                });

                return userArray;
            }, [users, sortConfig]);

            const sortedDeviceStats = useMemo(() => {
                return Object.entries(deviceStats).sort(([a], [b]) => a.localeCompare(b));
            }, [deviceStats]);

            return (
                <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 md:p-8">
                    <div className="max-w-7xl mx-auto">
                        <div className="mb-8 fade-in">
                            <div className="flex items-center justify-between mb-6">
                                <div>
                                    <h1 className="text-4xl md:text-5xl uppercase font-bold text-white mb-2 tracking-tight">
                                        99 NIGHT
                                    </h1>
                                    <p className="text-slate-400 text-sm md:text-base">Real-time monitoring dashboard • Powered by Supabase</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={handleCleanupOffline}
                                        className="px-4 py-2 bg-orange-600/20 hover:bg-orange-600/30 border border-orange-500/50 text-orange-400 rounded-lg text-sm font-medium transition-all duration-200"
                                    >
                                        🧹 Clean Offline
                                    </button>
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

                        {sortedDeviceStats.length > 0 && (
                            <div className="mb-8 fade-in">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                    {sortedDeviceStats.map(([device, data]) => (
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
                                            <th className="px-6 py-4 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Status
                                            </th>
                                            <th className="px-6 py-4 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Device
                                            </th>
                                            <th className="px-6 py-4 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Username
                                            </th>
                                            <th
                                                onClick={() => setSortConfig(prev => ({
                                                    key: 'diamonds',
                                                    direction: prev.key === 'diamonds' && prev.direction === 'desc' ? 'asc' : 'desc'
                                                }))}
                                                className="px-6 py-4 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider cursor-pointer select-none"
                                            >
                                                Diamonds
                                                <span className="ml-1 text-slate-500">
                                                    {sortConfig.key === 'diamonds'
                                                        ? sortConfig.direction === 'desc'
                                                            ? '▼'
                                                            : '▲'
                                                        : ''}
                                                </span>
                                            </th>
                                            <th className="px-6 py-4 text-center text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {isLoading ? (
                                            <tr>
                                                <td colSpan="5" className="px-6 py-16 text-center">
                                                    <div className="flex flex-col items-center gap-4">
                                                        <div className="w-16 h-16 border-4 border-slate-700 border-t-cyan-500 rounded-full animate-spin"></div>
                                                        <span className="text-slate-500 text-sm font-medium">Loading...</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ) : sortedUsers.length === 0 ? (
                                            <tr>
                                                <td colSpan="5" className="px-6 py-16 text-center">
                                                    <span className="text-slate-500 text-sm font-medium">No data available</span>
                                                </td>
                                            </tr>
                                        ) : (
                                            sortedUsers.map(user => (
                                                <UserRow 
                                                    key={user.username} 
                                                    user={user} 
                                                    onDelete={handleDeleteUser}
                                                />
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className="mt-6 text-center">
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 text-xs font-medium">
                                <span>Last updated: {lastUpdate || '--:--:--'}</span>
                                <span>•</span>
                                <span>Timeout: {STATUS_TIMEOUT / 1000}s</span>
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

# Cache for get_data endpoint
_cache = {'data': None, 'timestamp': 0}

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
        timestamp = int(time.time() * 1000)  # milliseconds

        # Convert diamonds to JSON string if dict/list
        if isinstance(diamonds, (dict, list)):
            diamonds = json.dumps(diamonds, separators=(',', ':'))
        else:
            diamonds = str(diamonds)

        # Upsert to Supabase
        result = supabase.table(TABLE_NAME).upsert({
            "username": username,
            "diamonds": diamonds,
            "device": device,
            "timestamp": timestamp
        }, on_conflict="username").execute()

        # Invalidate cache
        _cache['timestamp'] = 0

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_data", methods=["GET"])
def get_data():
    now = time.time()
    
    # Check cache
    if _cache['data'] and (now - _cache['timestamp']) < CACHE_TTL:
        return jsonify(_cache['data'])

    try:
        # Fetch all users from Supabase
        response = supabase.table(TABLE_NAME).select("*").execute()
        users = response.data

        result = []
        now_ms = int(now * 1000)
        
        for user in users:
            time_diff = (now_ms - user["timestamp"]) / 1000  # convert to seconds
            status = "ONLINE" if time_diff <= TIMEOUT else "OFFLINE"
            
            result.append({
                "username": user["username"],
                "diamonds": user["diamonds"],
                "device": user["device"],
                "status": status,
                "last_seen": int(time_diff)
            })
        
        # Update cache
        _cache['data'] = result
        _cache['timestamp'] = now
        
        return jsonify(result)
    except Exception as e:
        print(f"[ERROR] get_data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete_user", methods=["POST"])
def delete_user():
    try:
        data = request.json
        username = data.get("username")
        
        if not username:
            return jsonify({"status": "error", "message": "Username required"}), 400
        
        # Delete from Supabase
        supabase.table(TABLE_NAME).delete().eq("username", username).execute()
        
        # Invalidate cache
        _cache['timestamp'] = 0
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete_all", methods=["POST"])
def delete_all():
    try:
        # Delete all records from Supabase
        # Note: Supabase requires a filter, so we delete where timestamp > 0
        supabase.table(TABLE_NAME).delete().gt("timestamp", 0).execute()
        
        # Invalidate cache
        _cache['timestamp'] = 0
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/cleanup_offline", methods=["POST"])
def cleanup_offline():
    try:
        now_ms = int(time.time() * 1000)
        cutoff = now_ms - (TIMEOUT * 1000)
        
        # Delete offline users from Supabase
        result = supabase.table(TABLE_NAME).delete().lt("timestamp", cutoff).execute()
        
        # Invalidate cache
        _cache['timestamp'] = 0
        
        deleted_count = len(result.data) if result.data else 0
        return jsonify({"status": "success", "message": f"Removed {deleted_count} offline users"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.after_request
def compress_response(response):
    if response.status_code < 200 or response.status_code >= 300:
        return response
    
    accept_encoding = request.headers.get('Accept-Encoding', '')
    
    if 'gzip' not in accept_encoding.lower():
        return response
    
    if response.direct_passthrough:
        return response
    
    response.direct_passthrough = False
    response_data = response.get_data()
    
    if len(response_data) > 500:
        gzip_buffer = gzip.compress(response_data, compresslevel=6)
        response.set_data(gzip_buffer)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(gzip_buffer)
    
    return response

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Diamond Monitor with Supabase on port {port}")
    print(f"⏱️  Timeout: {TIMEOUT}s | Cache TTL: {CACHE_TTL}s")
    print(f"📊 Supabase URL: {SUPABASE_URL}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
