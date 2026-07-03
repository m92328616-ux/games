# XPilot (minimal)

A minimal XPilot-style top-down spaceship game. Rotate, thrust, shoot, and
destroy enemies for points. Three ways to play:

- **Desktop** (`xpilot.py`) — Python + `pygame`, multiplayer over UDP
- **Web / JavaScript** (`xpilot-web.html`) — runs in any browser, multiplayer over WebSocket
- **Web / Pyodide** (`xpilot-pyodide.html`) — same game, Python running in-browser via WebAssembly, multiplayer over WebSocket

Controls are the same everywhere: **Arrow keys / WASD** to rotate & thrust,
**Space** to shoot, **R** to restart after death (Esc to quit on desktop).
Web versions also have touch controls (joystick + buttons) for mobile.

Install dependencies first:

```bash
pip install -r requirements.txt
```
or you can install them one at a time using:

```bash
pip install pygame
pip install websockets
```
__Remember to install these in a virtual enviorment__

---

## How to install a virtual enviornment on Mac/Linux/Windows

To set up a virtual environment in Python using Visual Studio Code (VS Code), you can either use the VS Code Command Palette (automated method) or the built-in terminal (manual method).Before you start, make sure you have opened your project folder in VS Code (File > Open Folder...) and have the official Python extension installed.

**Easiest Method (The Command Pallete):**
1. By pressing ```Ctrl + Shift + P``` (Windows or Linux) or ```Cmd + Shift + P``` (Mac) 
2. Type **```Python: Create Enviorment```** and select it.
3. Choose **```Venv```** as your enviorment manager.
4. Select your preffered Python interpreter from the list.
5. Click **Yes** when VSCode asks you to automatically select it for your workspace folder.

**Manual Method: The Intergrated Method**

If you prefer using commands directly, open a new terminal in VS Code (Ctrl + \`\` or Terminal > New Terminal\`) and run the following based on your Operating System:

1. Create the Enviorment
    * Windows/Mac/Linux ```python -m venv .venv``` *(Note: Use ```python 3``` instead of ```python``` on Mac or Linux if required).*

2. Select the Interpreter
    1. Open the **Command Palatte**(```Ctrl/Cmd + Shift + P```).
    2. Type  and select **```Python: Select Interpreter```**
    3. Choose the option that starts with **```.venv```** from the list.

3. Activate the Envoirment 
    To make sure your terminal uses the virtual environment, close your current terminal window and open a new one (Terminal > New Terminal).Alternatively, you can manually activate it by running the script that matches your operating system:

    * **Windows (Powershell)**: ```.venv\Scripts\Activate.ps1```
    * **Windows (Command Prompt)**: ```.venv\Scripts\actvate.bat```
    * **Mac/Linux**: ```[source] .venv/bin/actvate```

    Once activated, you will see (.venv) appear at the very beginning of your terminal prompt line.

---

## Desktop version

Single player, no server needed:

```bash
python xpilot.py
```

### Multiplayer (LAN)

**1. Start the relay server** — on whichever machine will host the game:

```bash
python net_server.py --host 0.0.0.0 --port 50000
```

This also opens an HTTP status endpoint on port 8000 (`--http-port` to
change it). From any machine on the network:

```bash
curl http://SERVER_IP:8000/status
```

```json
{"clients": 2, "list": [{"ip": "192.168.1.100", "port": 51234}, {"ip": "192.168.1.101", "port": 51456}]}
```

**2. Connect clients** — on the host machine and on every friend's machine:

```bash
python xpilot.py --server SERVER_IP --port 50000
```

Replace `SERVER_IP` with the host's LAN IP (e.g. `192.168.1.100`) — or
`localhost` if you're connecting from the same machine that's running the
server.

**Stopping the server:** `Ctrl+C` in its terminal, or from another shell:

```bash
pkill -f "python.*net_server.py"
```

**If a friend can't connect:**
- Server must bind `0.0.0.0`, not `127.0.0.1` (see step 1 above)
- Allow UDP through the firewall: `sudo ufw allow 50000/udp`
- Behind a router/NAT, forward UDP port 50000 to the host machine
- Confirm both machines are on the same network and using the host's actual LAN IP
- Watch the server terminal for `Client joined: (ip, port)` — if it appears, the connection reached the server

---

## Web versions

Browsers can't speak the desktop version's raw UDP protocol, so the web
versions use a separate WebSocket relay (`ws_server.py`) and are served
as a website by `web-server.py`. Both web clients (JavaScript and
Pyodide) speak the same protocol, so people can mix and match — and
both fall back to single-player automatically if no relay is reachable.

### 1. Start the servers

```bash
python ws_server.py --host 0.0.0.0 --port 8765    # multiplayer relay
python web-server.py --host 0.0.0.0 --port 8000    # serves the website
```

### 2. Open the game

**On the same machine (localhost):**

```
http://localhost:8000/xpilot-web.html
http://localhost:8000/xpilot-pyodide.html
```

**Friends on the same network (LAN):** have them open the host machine's
LAN IP instead of `localhost`, e.g.:

```
http://192.168.1.100:8000/xpilot-web.html
```

Find the host's LAN IP with `ipconfig` (Windows) or `ifconfig` /
`ip addr` (Mac/Linux). Each page auto-connects to the relay on load — no
extra setup needed once both servers are running. The in-game HUD shows
"Connected · N other pilots online" once it works.

**Friends outside your network (internet):** the host's router needs to
forward TCP ports 8000 and 8765 to the host machine, and friends connect
to the host's public IP instead of the LAN IP. For anything beyond quick
testing, serving over HTTPS (below) is strongly recommended — plain HTTP
across the open internet is unencrypted and many browsers/networks will
flag or block it.

**Stopping the servers:** `Ctrl+C` in each terminal, or:

```bash
pkill -f "python.*web-server.py"
pkill -f "python.*ws_server.py"
```

### Serving over HTTPS

Recommended for anyone connecting from outside your LAN. Self-signed
certs are auto-generated on first run — good enough for testing, but
each visitor's browser will show a one-time "not private" warning they
need to click through:

```bash
python web-server.py --host 0.0.0.0 --port 8443 --https
```

```bash
curl -k https://localhost:8443/status
# -> {"status": "ok", "version": "web", "https": true, "port": 8443}
```

Friends then connect to `https://<host IP or domain>:8443/xpilot-web.html`.

For a public domain with no browser warning, use a real certificate
(e.g. from [Let's Encrypt](https://letsencrypt.org/) via `certbot`):

```bash
python web-server.py --host 0.0.0.0 --port 443 --https --cert fullchain.pem --key privkey.pem
```

Note: `ws_server.py` speaks plain `ws://`. If the page is loaded over
`https://`, browsers will only allow it to open `wss://` connections —
so for a fully-HTTPS public setup, put `ws_server.py` behind a reverse
proxy (nginx or Caddy) that terminates TLS on `wss://` and forwards to
`ws_server.py` on port 8765.

### Mobile

Both web versions are touch-optimized: a joystick (left side) for
rotate/thrust, and Thrust/Shoot/Restart buttons (right side). The canvas
scales to fit any screen size — phones, tablets, and desktops all work
from the same URL.