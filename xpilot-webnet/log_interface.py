"""
Centralized logging interface for XPilot.

Provides thread-safe logging with multiple levels and optional
real-time streaming to external terminal clients over TCP.

Usage from any module:
    from log_interface import get_logger
    log = get_logger("MyModule")
    log.info("Something happened")
    log.error("Something broke")

To enable TCP streaming (for external terminal clients):
    from log_interface import LogServer
    server = LogServer(port=9000)
    server.start()
    # ... later ...
    server.stop()

External terminals connect to localhost:9000 and receive one JSON
log line per TCP message.
"""
import socket
import threading
import time
import json
import sys
from datetime import datetime


# Log levels
DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

_LEVEL_NAMES = {
    DEBUG: "DEBUG",
    INFO: "INFO",
    WARNING: "WARNING",
    ERROR: "ERROR",
    CRITICAL: "CRITICAL",
}


class Logger:
    """Thread-safe logger that writes to local output and streams to connected terminals."""

    def __init__(self, source, level=DEBUG):
        self.source = source
        self.level = level

    def _log(self, level, message):
        if level < self.level:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_name = _LEVEL_NAMES.get(level, str(level))
        formatted = f"[{ts}] [{level_name}] [{self.source}] {message}"
        # Write to stderr so it doesn't interfere with pygame stdout usage
        print(formatted, file=sys.stderr, flush=True)
        # Broadcast to connected terminal clients
        _broadcast(level_name, ts, self.source, message)

    def debug(self, message):
        self._log(DEBUG, message)

    def info(self, message):
        self._log(INFO, message)

    def warning(self, message):
        self._log(WARNING, message)

    def error(self, message):
        self._log(ERROR, message)

    def critical(self, message):
        self._log(CRITICAL, message)


def get_logger(source, level=DEBUG):
    """Get a named logger instance.

    Args:
        source: Module/component name (e.g. "Game", "Network").
        level: Minimum log level to emit. Defaults to DEBUG.
    """
    return Logger(source, level)


# ---------------------------------------------------------------------------
# TCP log server – streams log entries to connected external terminals
# ---------------------------------------------------------------------------

# Global state for connected terminal clients
_clients = []          # list of connected socket objects
_clients_lock = threading.Lock()
_broadcast_queue = []  # list of formatted JSON strings waiting to be sent
_broadcast_lock = threading.Condition()


def _broadcast(level_name, timestamp, source, message):
    """Enqueue a log entry for all connected terminal clients (non-blocking)."""
    payload = json.dumps({
        "level": level_name,
        "time": timestamp,
        "source": source,
        "message": message,
    })
    with _broadcast_lock:
        _broadcast_queue.append(payload)
        _broadcast_lock.notify()


def _sender_loop():
    """Background thread that drains the broadcast queue and sends to all clients."""
    while True:
        with _broadcast_lock:
            while not _broadcast_queue:
                _broadcast_lock.wait(timeout=0.5)
            batch = list(_broadcast_queue)
            _broadcast_queue.clear()

        if not batch:
            continue

        dead = []
        with _clients_lock:
            targets = list(_clients)

        for sock in targets:
            for payload in batch:
                try:
                    sock.sendall((payload + "\n").encode("utf-8"))
                except Exception:
                    dead.append(sock)
                    break

        if dead:
            with _clients_lock:
                for s in dead:
                    try:
                        _clients.remove(s)
                    except ValueError:
                        pass
                    try:
                        s.close()
                    except Exception:
                        pass


class LogServer:
    """TCP server that external terminal clients connect to for real-time logs."""

    def __init__(self, host="127.0.0.1", port=9000):
        self.host = host
        self.port = port
        self._sock = None
        self._running = False
        self._accept_thread = None
        self._sender_thread = None

    def start(self):
        """Start the log server in background threads."""
        if self._running:
            return
        self._running = True

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind((self.host, self.port))
        except OSError:
            self._running = False
            self._sock.close()
            self._sock = None
            raise
        self._sock.listen(5)
        self._sock.settimeout(1.0)

        self._sender_thread = threading.Thread(
            target=_sender_loop, daemon=True, name="log-sender"
        )
        self._sender_thread.start()

        self._accept_thread = threading.Thread(
            target=self._accept_loop, daemon=True, name="log-accept"
        )
        self._accept_thread.start()
        print(f"[LogServer] Listening on {self.host}:{self.port}", file=sys.stderr)

    def _accept_loop(self):
        while self._running:
            try:
                client_sock, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with _clients_lock:
                _clients.append(client_sock)
            print(f"[LogServer] Terminal connected from {addr}", file=sys.stderr)

    def stop(self):
        """Shut down the log server and close all client connections."""
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        with _clients_lock:
            for s in _clients:
                try:
                    s.close()
                except Exception:
                    pass
            _clients.clear()


# Singleton server instance (created lazily by the game)
_log_server = None
_server_lock = threading.Lock()


def start_log_server(host="127.0.0.1", port=9000):
    """Start the singleton log server. Safe to call multiple times.

    If the port is already in use (e.g. another process is already
    serving logs on that port), this silently skips starting the TCP
    server — local stderr logging still works.
    """
    global _log_server
    with _server_lock:
        if _log_server is None:
            _log_server = LogServer(host, port)
            try:
                _log_server.start()
            except OSError:
                print(
                    f"[LogServer] Port {port} already in use — "
                    f"logging to stderr only (no external terminal).",
                    file=sys.stderr,
                )
                _log_server = None
        return _log_server


def stop_log_server():
    """Stop the singleton log server."""
    global _log_server
    with _server_lock:
        if _log_server is not None:
            _log_server.stop()
            _log_server = None
