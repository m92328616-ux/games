"""
WebSocket relay server for the XPilot web (browser) client.

Browsers cannot open raw UDP sockets, so the existing UDP relay
(net_server.py, used by the desktop pygame client xpilot.py) does not
work for xpilot-web.html / xpilot-pyodide.html. This server provides
the same kind of broadcast relay, but over WebSocket + JSON, for
browser clients — which is what makes "friends join over the
website" actually possible.

Protocol (JSON messages, one per WebSocket text frame):

  Client -> Server:
    {"type": "join", "id": "<client id>", "name": "<display name>"}
    {"type": "state", "id": "...", "x":.., "y":.., "angle":.., "vx":.., "vy":..,
     "dead": bool}
    {"type": "shoot", "id": "...", "x":.., "y":.., "vx":.., "vy":..}
    {"type": "enemies", "id": "...", "enemies": [...] }   # new: host broadcasts enemy state
    {"type": "leave", "id": "..."}

  Server -> Clients (broadcast to everyone except sender, plus a couple
  of server-originated message types):
    {"type": "state", "id": "...", ...}              (relayed)
    {"type": "shoot", "id": "...", ...}               (relayed)
    {"type": "enemies", "id": "...", ...}            (new: relayed from host)
    {"type": "player_joined", "id": "...", "name": "..."}
    {"type": "player_left", "id": "..."}
    {"type": "roster", "players": [...]}              (sent to the joiner only)

Usage:
    pip install websockets
    python ws_server.py --host 0.0.0.0 --port 8765
"""

import argparse
import asyncio
import json
import time
import http.server
import socketserver
import threading

try:
    import websockets
except ImportError:
    raise SystemExit(
        "Missing dependency 'websockets'. Install it with:\n"
        "    pip install websockets\n"
    )


# id -> {"ws": websocket, "name": str, "last_state": dict|None, "last_seen": float}
CLIENTS = {}
CLIENTS_LOCK = asyncio.Lock()

# Drop clients we haven't heard from in this many seconds (covers
# browser tab closes / network drops that don't cleanly close the
# socket).
STALE_TIMEOUT = 15.0


def now():
    return time.time()


async def broadcast(message_obj, exclude_id=None):
    """Send a JSON message to all connected clients except exclude_id."""
    data = json.dumps(message_obj)
    dead = []
    async with CLIENTS_LOCK:
        targets = [(cid, info["ws"]) for cid, info in CLIENTS.items() if cid != exclude_id]
    for cid, ws in targets:
        try:
            await ws.send(data)
        except Exception:
            dead.append(cid)
    if dead:
        async with CLIENTS_LOCK:
            for cid in dead:
                CLIENTS.pop(cid, None)


async def send_roster(ws, exclude_id):
    """Send the newly-joined client a snapshot of all current players."""
    async with CLIENTS_LOCK:
        roster = [
            {"id": cid, "name": info["name"], "state": info["last_state"]}
            for cid, info in CLIENTS.items()
            if cid != exclude_id and info["last_state"] is not None
        ]
    try:
        await ws.send(json.dumps({"type": "roster", "players": roster}))
    except Exception:
        pass


async def handler(ws):
    client_id = None
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except (ValueError, TypeError):
                continue

            mtype = msg.get("type")

            if mtype == "join":
                client_id = msg.get("id")
                if not client_id:
                    continue
                name = msg.get("name") or client_id[:6]
                async with CLIENTS_LOCK:
                    CLIENTS[client_id] = {
                        "ws": ws,
                        "name": name,
                        "last_state": None,
                        "last_seen": now(),
                    }
                print(f"Client joined: {client_id} ({name})")
                await send_roster(ws, client_id)
                await broadcast(
                    {"type": "player_joined", "id": client_id, "name": name},
                    exclude_id=client_id,
                )

            elif mtype == "state":
                cid = msg.get("id")
                if not cid:
                    continue
                async with CLIENTS_LOCK:
                    if cid in CLIENTS:
                        CLIENTS[cid]["last_state"] = msg
                        CLIENTS[cid]["last_seen"] = now()
                await broadcast(msg, exclude_id=cid)

            elif mtype == "shoot":
                cid = msg.get("id")
                async with CLIENTS_LOCK:
                    if cid in CLIENTS:
                        CLIENTS[cid]["last_seen"] = now()
                await broadcast(msg, exclude_id=cid)

            elif mtype == "enemies":
                # Forward enemy state sync from the host to all other clients
                cid = msg.get("id")
                await broadcast(msg, exclude_id=cid)

            elif mtype == "hit":
                # Non-host client reports a bullet hit on entity idx; relay to host
                cid = msg.get("id")
                if cid:
                    async with CLIENTS_LOCK:
                        if cid in CLIENTS:
                            CLIENTS[cid]["last_seen"] = now()
                await broadcast(msg, exclude_id=cid)

            elif mtype == "leave":
                cid = msg.get("id")
                if cid:
                    async with CLIENTS_LOCK:
                        CLIENTS.pop(cid, None)
                    await broadcast({"type": "player_left", "id": cid})

            # unknown message types are ignored

    except websockets.ConnectionClosed:
        pass
    finally:
        if client_id:
            async with CLIENTS_LOCK:
                CLIENTS.pop(client_id, None)
            print(f"Client left: {client_id}")
            await broadcast({"type": "player_left", "id": client_id})


async def reap_stale_clients():
    """Periodically drop clients that have gone silent without a clean close."""
    while True:
        await asyncio.sleep(5)
        cutoff = now() - STALE_TIMEOUT
        stale = []
        async with CLIENTS_LOCK:
            for cid, info in CLIENTS.items():
                if info["last_seen"] < cutoff:
                    stale.append(cid)
            for cid in stale:
                CLIENTS.pop(cid, None)
        for cid in stale:
            print(f"Client timed out: {cid}")
            await broadcast({"type": "player_left", "id": cid})


def start_http_status(http_port):
    """Background HTTP server exposing GET /status, mirroring net_server.py."""

    class StatusHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/status":
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            payload = {
                "clients": len(CLIENTS),
                "list": [
                    {"id": cid, "name": info["name"]}
                    for cid, info in CLIENTS.items()
                ],
            }
            self.wfile.write(json.dumps(payload).encode("utf8"))

        def log_message(self, format, *args):
            pass

    try:
        httpd = socketserver.TCPServer(("0.0.0.0", http_port), StatusHandler)
        httpd.allow_reuse_address = True
    except Exception as e:
        print(f"HTTP status server failed to start on port {http_port}: {e}")
        return
    print(f"HTTP status endpoint listening on 0.0.0.0:{http_port} (GET /status)")
    httpd.serve_forever()


async def main(host, port, http_port):
    if http_port:
        t = threading.Thread(target=start_http_status, args=(http_port,), daemon=True)
        t.start()

    asyncio.create_task(reap_stale_clients())

    async with websockets.serve(handler, host, port, ping_interval=10, ping_timeout=10):
        print(f"XPilot WebSocket relay listening on ws://{host}:{port}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket bind host")
    parser.add_argument("--port", default=8765, type=int, help="WebSocket bind port")
    parser.add_argument(
        "--http-port", default=8766, type=int,
        help="HTTP port for GET /status (0 to disable)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, args.port, args.http_port if args.http_port else None))
    except KeyboardInterrupt:
        print("Shutting down")