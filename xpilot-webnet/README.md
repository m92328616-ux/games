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

## Log Viewer (External Terminal)

XPilot includes a real-time logging system that streams log output from
the game and servers to an external terminal window. This is useful for
monitoring game events, network activity, and debugging without cluttering
the main game or server terminal.

### How it works

Every game process (desktop client, WebSocket server, web server) runs a
small TCP log server in the background. An external terminal script
connects to that server and displays every log entry as it arrives, with
color-coded severity levels:

| Level | Color | Meaning |
|-------|-------|---------|
| `DEBUG` | White | Verbose diagnostic info |
| `INFO` | Green | Normal events (score changes, connections) |
| `WARNING` | Yellow | Unexpected but recoverable situations |
| `ERROR` | Red | Failures (network drops, crashed connections) |
| `CRITICAL` | Magenta | Fatal errors |

### Quick start

**1. Open a separate terminal and start the log viewer:**

```bash
python log_terminal.py
```

This connects to `localhost:9000` by default and waits for log output.

**2. Start the game (or any server) in another terminal:**

```bash
python xpilot.py
```

Log entries immediately appear in the log viewer terminal:

```
Connected to log server at 127.0.0.1:9000
------------------------------------------------------------------------
[2026-07-12 14:30:01.123] [INFO   ] [Game    ] Game starting
[2026-07-12 14:30:01.124] [INFO   ] [Game    ] Display initialized: 800x600 @ 60 FPS
[2026-07-12 14:30:05.678] [INFO   ] [Game    ] Score: 10
[2026-07-12 14:30:08.234] [WARNING] [Game    ] Player died!
```

### Custom port

The desktop game client, WebSocket server, and web server all accept a
`--log-port` flag to change the TCP port (default `9000`). Both the
game/server and the log viewer must use the same port:

```bash
# Game on a custom port
python xpilot.py --log-port 9100

# Log viewer connecting to that port
python log_terminal.py --port 9100
```

### Remote monitoring

To monitor a game running on a different machine, pass `--host`:

```bash
python log_terminal.py --host 192.168.1.100 --port 9000
```

> **Note:** The log server binds to `127.0.0.1` (localhost only) by
> default for security. To allow remote connections, the game or server
> would need to bind to `0.0.0.0` — this is not yet exposed as a flag
> but can be changed in `log_interface.py`.

### Using with servers

The WebSocket server and web server also stream logs:

```bash
# Start servers
python ws_server.py --log-port 9000
python web-server.py --log-port 9000

# Watch all logs in one terminal
python log_terminal.py
```

Because each process runs its own log server on the same port, you can
only run **one** at a time on port 9000. If you need multiple processes
to stream to the same viewer, run each on a different port and open
multiple viewer instances:

```bash
# Different ports for each process
python xpilot.py --log-port 9001
python ws_server.py --log-port 9002
python log_terminal.py --port 9001
python log_terminal.py --port 9002
```

### Log message format

Each log entry is a JSON object sent as one line over TCP:

```json
{
  "level": "INFO",
  "time": "2026-07-12 14:30:01.123",
  "source": "Game",
  "message": "Score: 10"
}
```

This makes it easy to write custom log consumers or pipe output to other
tools.

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

---

## Synchronized screens (enemies in the same place for everyone)

**`xpilot-web.html`** now uses host-authoritative entity synchronization so
every connected player sees enemies at exactly the same positions.

### How it works

| Role | What it does |
|------|-------------|
| **HOST** (`[HOST]` shown in HUD) | Runs the authoritative entity simulation (positions, HP, AI, respawns). Broadcasts full enemy state to all peers at 12 Hz. |
| **CLIENT** (`[CLIENT]` shown in HUD) | Receives and applies the host's enemy state every ~83 ms. Runs entity physics locally between updates for smooth visuals. Sends `hit` reports to the host when a bullet connects. |

**Host election:** the player whose browser-generated ID is lexicographically
smallest becomes the host. If the host leaves, the next-lowest-ID client takes
over automatically within one heartbeat cycle.

**Kill reporting:** when a non-host bullet hits an enemy, the client:
1. Applies the kill locally (instant visual feedback + score).
2. Sends a `hit` message to the host with the entity index *and* generation
   counter (`gen`).
3. The host validates `gen` (stale hits targeting an already-respawned enemy
   are silently discarded), then applies damage and respawns the enemy.
4. The host's next entity broadcast corrects any local/remote divergence.

**Shooter AI** (enemies that fire back) runs exclusively on the host so all
clients see the same bullets coming from the same places.

**On disconnect:** each client immediately reclaims host authority so
single-player mode resumes at full fidelity without waiting for a timeout.

## Bugs / Issues

We ask you very politely to point out any bugs or glitches you may have encountered throughout these games. Create any issues for this repository if you have found any bugs. We will try to attend to every issue and create a fix. 

This is an open repository and all changes are welcomed except the ones that may undermine the foundations of these projects.

## Author's Notes:

This repository is a creation for games only. Explicit or malicious content will be flagged and removed off of the repository without an appeal as to so. Examples of such may include:

* NSFW or elxplicit content.
* Rude or offensive commentry on any part of this repository.
* Racist and sexual harm or violence will not be tolerated in this group project.
* Distributing malware or exploits using our repository or any files inside will easily be confronted with Github Staff even State Police and may get you in seriious consequences.
* Hosting sexually, obscene material, doxxing, and threatening violence will strictly break the rules and T&C's of ['Github's Acceptable Use Policies'](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)
* Please refrain of using such illict actions.

Thank you for following these rules set up here so we can maintain a happy community of people who want to code.

 - m92328616-ux