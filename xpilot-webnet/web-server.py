"""
Simple HTTP web server for XPilot web versions.
Serves HTML files and provides relay endpoints.

Usage:
    python web-server.py --port 8000
"""
import http.server
import socketserver
import argparse
import os
from pathlib import Path

PORT = 8000
SERVE_DIR = os.path.dirname(__file__)

class GameHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        """Serve files from the current directory."""
        path = path.split('?', 1)[0]  # Remove query string
        path = path.split('#', 1)[0]  # Remove fragment
        if path == '/':
            path = '/xpilot-web.html'
        path = super().translate_path(path)
        return path

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/':
            self.path = '/xpilot-web.html'
        
        if self.path in ['/xpilot-web.html', '/xpilot-pyodide.html']:
            file_path = os.path.join(SERVE_DIR, self.path.lstrip('/'))
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
        
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "version": "web"}')
            return
        
        super().do_GET()

    def log_message(self, format, *args):
        """Quiet logging."""
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='XPilot Web Server')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    args = parser.parse_args()

    os.chdir(SERVE_DIR)
    
    Handler = GameHTTPHandler
    with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
        print(f'XPilot Web Server listening on {args.host}:{args.port}')
        print(f'  → http://localhost:{args.port}/xpilot-web.html (JavaScript version)')
        print(f'  → http://localhost:{args.port}/xpilot-pyodide.html (Python/Pyodide version)')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('Shutting down...')
