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

See [`xpilot-webnet/README.md`](xpilot-webnet/README.md) for full setup instructions, including running the multiplayer relay server, the web server, and troubleshooting network connectivity.

**Quick start (desktop):**
```bash
cd xpilot-webnet
pip install -r requirements.txt
python xpilot.py
```

**Quick start (browser):**
```bash
cd xpilot-webnet
python web-server.py --port 8000
# then open http://localhost:8000/xpilot-web.html
```

## Getting Started

Clone the repository:
```bash
git clone https://github.com/m92328616-ux/games.git
cd games
```

Each game can be run independently — see the sections above for specific instructions.

## License

No license file is currently included. Add one if you intend to share or accept contributions to this project.
