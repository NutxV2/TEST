# server.py
import asyncio
import websockets
import json
from datetime import datetime

USERS = {}  # username -> last_seen timestamp
CLIENTS = set()

STATUS_TIMEOUT = 5  # วินาที

async def broadcast_status():
    while True:
        now = datetime.now().timestamp()
        status_list = []
        for username, last_seen in USERS.items():
            status = "ONLINE" if now - last_seen <= STATUS_TIMEOUT else "OFFLINE"
            status_list.append({"username": username, "status": status})
        if CLIENTS:
            message = json.dumps(status_list)
            await asyncio.wait([client.send(message) for client in CLIENTS])
        await asyncio.sleep(1)

async def handler(websocket, path):
    CLIENTS.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            username = data.get("username")
            if username:
                USERS[username] = datetime.now().timestamp()
    except:
        pass
    finally:
        CLIENTS.remove(websocket)

async def main():
    server = await websockets.serve(handler, "0.0.0.0", 5000)
    asyncio.create_task(broadcast_status())
    await server.wait_closed()

asyncio.run(main())
