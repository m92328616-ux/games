"""
Simple UDP relay server for the XPilot minimal game.
Run on a machine reachable by clients.

Usage:
    python net_server.py --host 0.0.0.0 --port 50000

The server starts an HTTP status endpoint on port 8000 by default.
"""
import socket
import argparse
import time
import threading
import http.server
import socketserver
import json


def run(host, port, http_port=8000):
    if http_port is None:
        http_port = 8000
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    print(f"Relay server listening on {host}:{port}")
    
    clients = set()
    clients_lock = threading.Lock()

    def start_http(http_port):
        """Start HTTP status endpoint in background thread."""
        class StatusHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/status':
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                # snapshot clients
                with clients_lock:
                    cl = list(clients)
                payload = {'clients': len(cl), 'list': [{'ip': c[0], 'port': c[1]} for c in cl]}
                self.wfile.write(json.dumps(payload).encode('utf8'))

            def log_message(self, format, *args):
                pass  # suppress default logging

        try:
            httpd = socketserver.TCPServer(('0.0.0.0', http_port), StatusHandler)
            httpd.allow_reuse_address = True
        except Exception as e:
            print(f'HTTP status server failed to start on port {http_port}:', e)
            return
        print(f'HTTP status endpoint listening on 0.0.0.0:{http_port} (GET /status)')
        httpd.serve_forever()

    # Start HTTP server in background if requested
    if http_port:
        http_t = threading.Thread(target=start_http, args=(http_port,), daemon=True)
        http_t.start()

    try:
        while True:
            try:
                data, addr = sock.recvfrom(8192)
            except Exception:
                continue
            # register client
            with clients_lock:
                if addr not in clients:
                    clients.add(addr)
                    print("Client joined:", addr)
            # broadcast to others
            dead = []
            with clients_lock:
                for c in list(clients):
                    if c == addr:
                        continue
                    try:
                        sock.sendto(data, c)
                    except Exception:
                        dead.append(c)
            if dead:
                with clients_lock:
                    for d in dead:
                        try:
                            clients.remove(d)
                        except KeyError:
                            pass
    except KeyboardInterrupt:
        print("Shutting down")
    finally:
        sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='UDP bind host')
    parser.add_argument('--port', default=50000, type=int, help='UDP bind port')
    parser.add_argument('--http-port', default=8000, type=int, help='HTTP port for GET /status (default: 8000)')
    args = parser.parse_args()
    run(args.host, args.port, args.http_port)





