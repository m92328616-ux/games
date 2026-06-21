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

Web Multiplayer (see other players live)

Both browser versions — `xpilot-web.html` (JavaScript) and
`xpilot-pyodide.html` (Python via WebAssembly) — support a much
larger 8000x6000 world with a zoomable camera and a minimap (top-left
corner), plus optional live multiplayer: when other people open
either page against the same relay server, you'll see their ships,
names, and shots in real time. The two clients are protocol-
compatible, so a JS-client player and a Pyodide-client player can be
in the same game together.

Browsers can't speak raw UDP (which is what `net_server.py` /
`xpilot.py` use), so a separate relay is included for the web clients:

```bash
pip install -r requirements.txt
python ws_server.py --host 0.0.0.0 --port 8765
```

Then serve the pages as usual:

```bash
python web-server.py --port 8000
```

Open `http://localhost:8000/xpilot-web.html` or
`http://localhost:8000/xpilot-pyodide.html` in as many browser tabs /
machines as you like, in any combination. Each tab auto-connects to
`ws://<page host>:8765` on load — no extra setup needed as long as
`ws_server.py` is running on the same host that served the page. If
it can't connect, the game still works fine single-player; the status
line in the top-right corner shows "Offline (single player)" vs
"Connected".

For LAN play: run `ws_server.py` on one machine with `--host 0.0.0.0`,
then have other players open `http://<that machine's LAN IP>:8000/xpilot-web.html`
(or the `-pyodide.html` page).

Controls (unchanged), plus:

- Mouse wheel / pinch: zoom in and out
- `+` / `-` keys: zoom in and out
- Minimap (top-left): shows the whole 8000x6000 world, all players'
  positions, and a white rectangle marking your current camera view
  and zoom level

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

- Python runs directly in the browser (game simulation — physics,
  enemies, collisions — is real Python via Pyodide)
- Requires internet access on first load to fetch the Pyodide runtime
  from a CDN; not fully offline
- Open: http://localhost:8000/xpilot-pyodide.html
- Slightly slower to start (Pyodide download/init) but otherwise has
  full feature parity with the JavaScript version: the same
  8000x6000 world, camera zoom, minimap, and live multiplayer over
  `ws_server.py`

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

Both versions feature the same gameplay — rotate, thrust, shoot, and destroy enemies for points — across a shared 8000x6000 world with camera zoom and a minimap. Both also support live multiplayer (see "Web Multiplayer" above) via `ws_server.py`; without it running, each falls back to single-player automatically.

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