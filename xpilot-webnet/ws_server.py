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
    {"type": "pickup_request", "id": "...", "pickupId": "..."}  # collect a power-up
    {"type": "pickup_hit", "id": "...", "pickupId": "...", "dmg": int,
     "firedBy": "player"|"enemy"}                            # bullet damaged a power-up
    {"type": "player_hit", "id": "...", "target": "...", "dmg": int}  # PvP hit report
    {"type": "player_hp", "id": "...", "hp": int, "dead": bool,
     "killer": "..."}                                   # host-authoritative PvP HP
    {"type": "player_respawn", "id": "..."}             # player wants to respawn
    {"type": "leave", "id": "..."}

  Server -> Clients (broadcast to everyone except sender, plus a couple
  of server-originated message types):
    {"type": "state", "id": "...", ...}              (relayed)
    {"type": "shoot", "id": "...", ...}               (relayed)
    {"type": "enemies", "id": "...", ...}            (new: relayed from host)
    {"type": "player_joined", "id": "...", "name": "..."}
    {"type": "player_left", "id": "..."}
    {"type": "roster", "players": [...]}              (sent to the joiner only)
    {"type": "player_hit", ...}                       (relayed, host applies)
    {"type": "player_hp", ...}                        (relayed, all clients apply)
    {"type": "player_respawn", ...}                   (relayed, host resets HP)

  Server -> Clients (server-authoritative power-up sync):
    {"type": "pickup_state", "seq": int, "pickups": [...]}       (full snapshot)
    {"type": "pickup_spawned", "pickup": {...}}
    {"type": "pickup_picked", "pickup": {...}, "by": "...", "kind": "..."}
    {"type": "pickup_damaged", "pickup": {...}, "by": "...",
     "destroyed": bool, "primed": bool}
    {"type": "pickup_exploded", "pickup": {...}, "x":.., "y":.., "blastRadius":..}

  The relay server is the sole authority for power-up state: it owns the
  spawn/respawn timers, assigns unique IDs, validates collection and
  damage requests, and periodically broadcasts snapshots so clients stay
  in sync (and late joiners receive the current state immediately).

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

from log_interface import (
    get_logger,
    parse_forward_address,
    set_log_level,
    start_log_forward,
    start_log_server,
    stop_log_forward,
    stop_log_server,
)
from pickup_sync import PowerUpManager

log = get_logger("WSServer")

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

# Server-authoritative power-up state (see pickup_sync.py). Owned by the
# relay server so every client sees identical power-ups at identical spots.
POWERUP_MANAGER: "PowerUpManager | None" = None
POWERUP_TICK_DT = 0.1          # simulation step for respawn/fuse timers
POWERUP_SYNC_HZ = 4.0          # authoritative full-state snapshot rate

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
                log.info(f"Client joined: {client_id} ({name})")
                await send_roster(ws, client_id)
                # Send the joiner the authoritative power-up state immediately
                # so they spawn with the exact same pickups as everyone else.
                if POWERUP_MANAGER is not None:
                    try:
                        await ws.send(json.dumps(POWERUP_MANAGER.snapshot_message()))
                    except Exception:
                        pass
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

            elif mtype == "pickups":
                # Forward pickup state sync from the host to all other clients
                cid = msg.get("id")
                await broadcast(msg, exclude_id=cid)

            elif mtype == "pickup_request":
                # Client wants to collect a power-up. The server validates the
                # request (pickup must exist, be active, and the client must be
                # close enough) and broadcasts the result to everyone.
                cid = msg.get("id")
                pid = msg.get("pickupId")
                if not cid or not pid or POWERUP_MANAGER is None:
                    continue
                player_pos = None
                async with CLIENTS_LOCK:
                    if cid not in CLIENTS:
                        continue
                    last_state = CLIENTS[cid]["last_state"]
                    if last_state is not None and last_state.get("x") is not None:
                        player_pos = (last_state.get("x"), last_state.get("y"))
                    CLIENTS[cid]["last_seen"] = now()
                ev = POWERUP_MANAGER.try_collect(pid, cid, player_pos)
                if ev:
                    await broadcast(ev)

            elif mtype == "pickup_hit":
                # A bullet hit a power-up. The server validates and applies the
                # damage, then broadcasts the authoritative result.
                cid = msg.get("id")
                pid = msg.get("pickupId")
                if not cid or not pid or POWERUP_MANAGER is None:
                    continue
                async with CLIENTS_LOCK:
                    if cid not in CLIENTS:
                        continue
                    CLIENTS[cid]["last_seen"] = now()
                dmg = msg.get("dmg", 1)
                ev = POWERUP_MANAGER.apply_damage(pid, dmg, cid)
                if ev:
                    await broadcast(ev)

            elif mtype == "hit":
                # Non-host client reports a bullet hit on entity idx; relay to host
                cid = msg.get("id")
                if cid:
                    async with CLIENTS_LOCK:
                        if cid in CLIENTS:
                            CLIENTS[cid]["last_seen"] = now()
                await broadcast(msg, exclude_id=cid)

            elif mtype in ("player_hit", "player_hp", "player_respawn"):
                # PvP messages. The relay server does not own PvP state (the
                # host-elected client is authoritative), so it simply relays:
                #   * player_hit      — non-host reports damage to the host
                #   * player_hp       — host broadcasts authoritative HP to all
                #   * player_respawn  — a player asks the host to reset their HP
                #
                # The sender's socket never needs its own message back: for
                # player_hit/player_respawn the sender authored it, and for
                # player_hp the sender (the host) already holds the state it
                # just broadcast. So exclude by the connection's client_id
                # rather than by the message's "id" field, which for
                # player_hp names the *affected* player (the target) and must
                # still reach that client.
                if client_id:
                    async with CLIENTS_LOCK:
                        if client_id in CLIENTS:
                            CLIENTS[client_id]["last_seen"] = now()
                await broadcast(msg, exclude_id=client_id)

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
            log.info(f"Client left: {client_id}")
            await broadcast({"type": "player_left", "id": client_id})


async def powerup_loop():
    """Server-authoritative power-up simulation + periodic snapshots."""
    if POWERUP_MANAGER is None:
        return
    snap_accum = 0.0
    while True:
        await asyncio.sleep(POWERUP_TICK_DT)
        for ev in POWERUP_MANAGER.tick(POWERUP_TICK_DT):
            await broadcast(ev)
        snap_accum += POWERUP_TICK_DT
        if snap_accum >= 1.0 / POWERUP_SYNC_HZ:
            snap_accum = 0.0
            await broadcast(POWERUP_MANAGER.snapshot_message())


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
            log.warning(f"Client timed out: {cid}")
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
        log.error(f"HTTP status server failed to start on port {http_port}: {e}")
        return
    log.info(f"HTTP status endpoint listening on 0.0.0.0:{http_port} (GET /status)")
    httpd.serve_forever()


async def main(host, port, http_port):
    global POWERUP_MANAGER
    if http_port:
        t = threading.Thread(target=start_http_status, args=(http_port,), daemon=True)
        t.start()

    POWERUP_MANAGER = PowerUpManager()
    log.info(f"Server-authoritative power-up system active: {len(POWERUP_MANAGER.pickups)} pickups")

    asyncio.create_task(reap_stale_clients())
    asyncio.create_task(powerup_loop())

    async with websockets.serve(handler, host, port, ping_interval=10, ping_timeout=10):
        log.info(f"XPilot WebSocket relay listening on ws://{host}:{port}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket bind host")
    parser.add_argument("--port", default=8765, type=int, help="WebSocket bind port")
    parser.add_argument(
        "--http-port", default=8766, type=int,
        help="HTTP port for GET /status (0 to disable)",
    )
    parser.add_argument("--log-port", type=int, default=9000, help="TCP port for external log terminal (default: 9000)")
    parser.add_argument(
        "--log-level", default="debug",
        choices=("debug", "info", "warning", "error", "critical"),
        help="Minimum log level to emit (default: debug)",
    )
    parser.add_argument(
        "--log-forward", default=None, metavar="HOST:PORT",
        help="Instead of hosting a log listener, push all log entries to a "
             "central log server at HOST:PORT (e.g. 127.0.0.1:9000)",
    )
    args = parser.parse_args()

    set_log_level(args.log_level)
    if args.log_forward:
        fwd_host, fwd_port = parse_forward_address(args.log_forward)
        start_log_forward(fwd_host, fwd_port)
    else:
        start_log_server(port=args.log_port)
    try:
        asyncio.run(main(args.host, args.port, args.http_port if args.http_port else None))
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        stop_log_server()
        stop_log_forward()