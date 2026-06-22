# XPilot (minimal) — Python

Minimal XPilot-style top-down spaceship game implemented in Python using `pygame`.

Requirements:

- Python 3.8+
- `pygame` (see `requirements.txt`)

Run:

```bash
python xpilot.py
```

Controls:

- Arrow keys / WASD: rotate & thrust
- Space: shoot
- R: restart after death
- Esc: quit

Multiplayer (local network):

- Run the relay server on a reachable host:

```bash
python net_server.py --host 0.0.0.0 --port 50000
```

- To stop the relay server, press `Ctrl+C` in the terminal where it is running.

- If the server is running in the background or needs to be terminated from another shell, use:

```bash
pkill -f "python.*net_server.py"
```

- Start clients connecting to that server:

```bash
python xpilot.py --server SERVER_HOST --port 50000
```

Replace `SERVER_HOST` with the server IP or hostname.

HTTP Status Endpoint

The relay server includes an HTTP status endpoint for checking connectivity and active clients. It is enabled by default on port 8000.

Start the server:

```bash
python net_server.py --host 0.0.0.0 --port 50000
```

If you want to change the HTTP port, pass `--http-port`:

```bash
python net_server.py --host 0.0.0.0 --port 50000 --http-port 8001
```

Query the status (from any machine):

```bash
curl http://SERVER_IP:8000/status
```

Example response:

```json
{
  "clients": 2,
  "list": [
    {"ip": "192.168.1.100", "port": 51234},
    {"ip": "192.168.1.101", "port": 51456}
  ]
}
```

Connection Troubleshooting

If your client cannot reach the relay server, try the following checks and fixes:

- Ensure the server is listening on all interfaces (bind to 0.0.0.0):

```bash
python net_server.py --host 0.0.0.0 --port 50000
```

- Verify the server is listening on the UDP port (server machine):

```bash
ss -lun | grep 50000
```

- From the client machine, send a quick UDP probe (replace SERVER_IP):

```bash
python - <<'PY'
import socket, json
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.sendto(json.dumps({'type':'state','id':'probe','x':10,'y':20}).encode(),('SERVER_IP',50000))
print('probe sent')
PY
```

- Or (Bash):

```bash
echo -n '{"type":"state","id":"probe"}' > /dev/udp/SERVER_IP/50000
```

- Check server terminal for a join message like `Client joined: (client_ip, client_port)` — if you see it, the packet arrived.

- If no join appears, common causes:
	- Server bound to `127.0.0.1` only (use `--host 0.0.0.0`).
	- Firewall blocking UDP 50000 (allow it, e.g. `sudo ufw allow 50000/udp`).
	- Server behind NAT — forward UDP port 50000 from router to server.
	- Wrong IP/hostname used on the client.

- For LAN testing ensure both machines are on the same network and you use the server's LAN IP.

If you'd like, I can make the server default to `0.0.0.0` and add verbose logging or add a TCP health-check endpoint — tell me which you prefer.

Web Versions (Browser-based)

XPilot is also available in two web-based versions — no Python installation needed on the client!

**JavaScript Version** (recommended for web):

- Fast, optimized for browser
- Run via web server:

```bash
python web-server.py --port 8000
```

- Open in browser: http://localhost:8000/xpilot-web.html
- Same controls and gameplay as desktop version

**Pyodide Version** (Python in WebAssembly):

- Python runs directly in the browser
- No server needed (works offline)
- Open: http://localhost:8000/xpilot-pyodide.html
- Slightly slower but showcases Python on web

Usage:

1. Start the web server:

```bash
python web-server.py --port 8000 
```

2. Stop the web server with `Ctrl+C` in the terminal.

   If the server needs to be terminated from another shell:

```bash
pkill -f "python.*web-server.py"
```

3. Open a browser to:
   - **JavaScript**: http://localhost:8000/xpilot-web.html
   - **Pyodide**: http://localhost:8000/xpilot-pyodide.html

Both versions feature the same gameplay — rotate, thrust, shoot, and destroy enemies for points. The web versions are single-player only (no relay networking yet).

Mobile Support

Both web versions are fully mobile-optimized with touch controls:

**Touch Controls (Mobile):**

- **Left area (Joystick)**: Tilt left/right to rotate, up to thrust
- **Right buttons**:
  - Thrust: Hold to accelerate
  - Shoot: Tap to fire
  - Restart: Appears when dead

**Desktop Controls (Keyboard):**

- Arrow keys / WASD: rotate & thrust
- Space: shoot
- R: restart

Works on phones, tablets, and desktops. The canvas scales to fit any screen size.
