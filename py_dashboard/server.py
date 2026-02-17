import json
import os
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import queue
import time

# Logging to file
def log_debug(msg):
    with open("dashboard_server.log", "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
    print(msg)

# Queue of messages to send to connected browsers (SSE)
event_queues = []

# Global Cache for Last Broadcast
last_broadcast = {} # {payload_type: data_dict}

class DashboardHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Override to add CORS and Cache headers globally if needed, 
        # or just let send_response handle specific headers.
        # Check if we need to add Cache-Control for index.html here or in send_response.
        # send_response is better for headers that depend on the response code.
        super().end_headers()

    def do_GET(self):
        if self.path == "/":
            self.path = "/py_dashboard/index.html"
        
        if self.path == "/events":
            self.handle_sse()
            return
            
        # For all other GET requests (static files), use default handler
        # Disable caching for index.html via end_headers or send_response logic below
        return super().do_GET()

    def handle_sse(self):
        # SSE Endpoint
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        q = queue.Queue()
        event_queues.append(q)
        log_debug(f"📡 SSE Client connected. Active: {len(event_queues)}")
        
        # IMMEDIATE PUSH: Send cached data to new client
        if last_broadcast:
            for p_type, data in last_broadcast.items():
                log_debug(f"  -> Pushing cached {p_type} to new client")
                q.put(data)
        
        try:
            # Keep connection open and send data from queue
            while True:
                try:
                    data = q.get(timeout=10) # 10s heartbeat
                    self.wfile.write(f"data: {json.dumps(data)}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except Exception as e:
            log_debug(f"🔌 SSE Client disconnected: {e}")
        finally:
            if q in event_queues:
                event_queues.remove(q)

    def do_POST(self):
        if self.path != "/broadcast":
             self.send_error(404, "Path not found")
             return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            p_type = data.get('payload_type', 'UNKNOWN')
            
            # Update Cache
            last_broadcast[p_type] = data
            
            log_debug(f"🚀 Broadcasting via SSE: {data.get('msg_type')} ({p_type}) to {len(event_queues)} clients")
            # Push to all active SSE queues
            for q in event_queues:
                q.put(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "clients": len(event_queues)}).encode())
        except Exception as e:
            import traceback
            traceback.print_exc()
            log_debug(f"POST Error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    # Override log_message to prevent recursion from stderr
    def log_message(self, format, *args):
        pass 

    def log_error(self, format, *args):
        pass

def run_http_server():
    server_address = ('', 8000)
    httpd = ThreadingHTTPServer(server_address, DashboardHandler)
    log_debug("🚀 Dashboard SSE Server running on http://localhost:8000 (Threaded)")
    httpd.serve_forever()

if __name__ == "__main__":
    log_debug("--- Dashboard SSE Server Starting ---")
    run_http_server()
