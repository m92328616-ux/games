# Games

A small collection of Python games and experiments, ranging from classic terminal/desktop games to a multiplayer space shooter with browser-based clients.

## Contents

### Snake (`snake.py`)
A classic Snake game built with Python's built-in `turtle` graphics module. Eat food to grow, avoid hitting your own tail, and try to beat the high score.

**Run:**
```bash
python snake.py
```

**Requirements:** Python 3 (uses the standard library `turtle` module — no extra installs needed).

### Pong (`pong.py`)
A Pong clone built with `tkinter`, featuring an AI opponent that predicts ball trajectory (with a bit of intentional error to keep things fair).

**Run:**
```bash
python pong.py
```

**Requirements:** Python 3 (uses the standard library `tkinter` module — no extra installs needed).

### XPilot Web/Net (`xpilot-webnet/`)
A minimal XPilot-style top-down spaceship shooter, available in three flavors:

- **Desktop (Python/pygame):** the original game with optional local-network multiplayer via a relay server.
- **Browser (JavaScript):** a fast, single-player web version served over HTTP — no Python install needed on the client.
- **Browser (Pyodide):** Python running directly in the browser via WebAssembly — works offline once loaded.

Controls: arrow keys/WASD to rotate and thrust, Space to shoot, R to restart, Esc to quit. Touch controls are supported on mobile for the web versions.

See [`xpilot-webnet/README.md`](xpilot-webnet/README.md) for full setup instructions, including multiplayer, HTTPS, and network troubleshooting.

**Quick start (desktop):**
```bash
cd xpilot-webnet
pip install -r requirements.txt
python xpilot.py
```

**Quick start (browser):**
```bash
cd xpilot-webnet
pip install websockets
python ws_server.py --host 0.0.0.0 --port 8765   # WebSocket relay (multiplayer)
python web-server.py --port 8000                   # serves the game files
# then open http://localhost:8000/xpilot-web.html
```

#### WebSocket relay (`ws_server.py`)

Browsers can't use the desktop UDP relay, so the web versions use a WebSocket relay instead. Both web clients (JavaScript and Pyodide) connect to it automatically on load — no extra setup in the browser.

**Start the relay:**
```bash
python ws_server.py --host 0.0.0.0 --port 8765
```

This also opens an HTTP status endpoint on port 8766 by default:
```bash
curl http://localhost:8766/status
# -> {"clients": 2, "list": [{"id": "...", "name": "..."}]}
```

**Friends on the same network (LAN):** have them open the host machine's LAN IP, e.g. `http://192.168.1.100:8000/xpilot-web.html` — the page auto-connects to the relay, no extra steps needed.

**Friends over the internet:** forward TCP ports `8000` and `8765` on your router to the host machine, and share your public IP. For anything beyond quick testing, serving over HTTPS is recommended — see `xpilot-webnet/README.md` for instructions.

**Stop the servers:**
```bash
pkill -f "python.*ws_server.py"
pkill -f "python.*web-server.py"
```

Stale clients (e.g. closed browser tabs that didn't disconnect cleanly) are automatically dropped after 15 seconds.

## Getting Started

Clone the repository:
```bash
git clone https://github.com/m92328616-ux/games.git
cd games
```

Each game can be run independently — see the sections above for specific instructions.

## License

No license file is currently included. Add one if you intend to share or accept contributions to this project.
Large files such as [`xpilot-webnet/`](xpilot-webnet/) would have to go through thorough checks to continue.

## Bugs / Issues

We ask you very politely to point out any bugs or glitches you may have encountered throughout these games. Create any issues for this repository if you have found any bugs. We will try to attend to every issue and create a fix. 

This is an open repository and all changes are welcomed except the ones that may undermine the foundations of these projects.

## Author's Notes:

This repository is a creation for games only. Explicit or malicious content will be flagged and removed off of the repository without an appeal as to so. Examples of such may include:

* NSFW or elxplicit content.
* Rude or offensive commentry on any part of this repository.
* Racist and sexual harm or violence will not be tolerated in this group project.
* Distributing malware or exploits using our repository or any files inside will easily be confronted with Github Staff and may get you in serious consequences.
* Hosting sexually, obscene material, doxxing, and threatening violence will strictly break the rules and T&C's of ['Github's Acceptable Use Policies'](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)
* Please refrain of using such illict actions.
* Please read [`LICENSE`](LICENSE) and for further evaluation on responisibilities of this repository.
* Please read our Code of Conduct to follow up on saftey guidelines and procedures of this repository.

Thank you for following these rules set up here so we can maintain a happy community of people who want to code.

 - m92328616-ux
