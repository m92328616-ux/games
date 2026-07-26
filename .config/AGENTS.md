# AGENTS.md

## Repo structure

- `snake.py`, `pong.py` — standalone games, stdlib only (turtle, tkinter). Run directly with `python <file>`.
- `xpilot-webnet/` — multiplayer spaceship shooter (Python/pygame + browser JS + Pyodide). Has its own `requirements.txt` (`pygame`, `websockets`).
  - `xpilot.py` — desktop client (pygame)
  - `ws_server.py` — WebSocket relay for browser clients
  - `web-server.py` — static file server for browser clients
  - `fuel-system.js`, `pickup-system.js` — browser-side game modules
  - `tests/` — JS tests using Node's built-in test runner (`node --test`)

## Running tests

```bash
# JS unit tests (fuel/pickup systems)
node --test xpilot-webnet/tests/

# No Python tests or linter configured in this repo.
```

## OpenCode Configuration
Enable language server protocol (LSP) feedback for this project.

```json:opencode.json
{
  "lsp": true
}
```



## Key quirks

- Browser clients auto-connect to `ws_server.py` on `ws://localhost:8765`. No client-side config needed for local dev.
- `ws_server.py` also exposes an HTTP status endpoint on port 8766.
- Stale WebSocket clients are dropped after 15 seconds of inactivity.
- No formatter, linter, type-checker, or CI pipeline is configured. Do not assume `npm`, `pip`, or any package manager beyond what is listed here.
- The `xpilot-webnet/` directory is large; avoid adding bulk generated or binary files there.
