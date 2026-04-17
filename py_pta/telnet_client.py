import socket
import json
import time
import threading
from typing import Optional, Dict, Any, Callable

class TelChatClient:
    """
    TCP client for communicating with the TelChat Hub.
    Handles registration, heartbeats, and message routing.
    """
    def __init__(self, host: str, port: int, alias: str):
        self.host = host
        self.port = port
        self.alias = alias
        self.sock: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        self.on_message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.last_send_time = 0

    def connect(self) -> bool:
        """Establishes connection and registers with the hub."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            
            # Phase 1: Registration
            registration_msg = {
                "from": self.alias,
                "to": "router",
                "msg_type": "registration",
                "timestamp": time.time(),
                "byte_count": len(json.dumps({"alias": self.alias}).encode("utf-8")),
                "data": {"alias": self.alias}
            }
            self._send_raw(json.dumps(registration_msg))
            
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Start heartbeat thread
            threading.Thread(target=self._heartbeat_loop, daemon=True).start()
            
            print(f"✅ Connected to TelChat Hub at {self.host}:{self.port} as '{self.alias}'")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def _send_raw(self, line: str):
        """Sends a raw string with a newline."""
        if self.sock:
            try:
                self.sock.sendall((line + "\n").encode("utf-8"))
                self.last_send_time = time.time()
            except socket.error:
                self.running = False

    def send(self, to: str, msg_type: str, data: Dict[str, Any]):
        """Sends a structured JSON message."""
        payload = json.dumps(data)
        msg = {
            "from": self.alias,
            "to": to,
            "msg_type": msg_type,
            "timestamp": time.time(),
            "byte_count": len(payload.encode("utf-8")),
            "data": data
        }
        self._send_raw(json.dumps(msg))

    def _receive_loop(self):
        """Background thread to read lines from the socket."""
        buffer = b""
        while self.running:
            try:
                chunk = self.sock.recv(1024)
                if not chunk:
                    print("📡 Connection closed by server.")
                    self.running = False
                    break
                
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    
                    try:
                        msg = json.loads(line.decode("utf-8"))
                        if self.on_message_callback:
                            self.on_message_callback(msg)
                    except json.JSONDecodeError:
                        print(f"⚠️ Received malformed JSON: {line}")
            except Exception as e:
                if self.running:
                    print(f"⚠️ Receive error: {e}")
                self.running = False
                break

    def _heartbeat_loop(self):
        """Sends a heartbeat every 45 seconds to keep the connection alive."""
        while self.running:
            time.sleep(10)
            if time.time() - self.last_send_time > 45:
                # Send a simple heartbeat ACK or data message
                self.send(to="router", msg_type="ack", data={"heartbeat": True})

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
