from .client import IBKRClient
from typing import Optional

# Global Active Client (Singleton)
_ACTIVE_CLIENT: Optional[IBKRClient] = None

def get_active_client() -> IBKRClient:
    """
    Liefert den global aktiven, verbundenen Client.
    Crasht, wenn keine Verbinudung besteht.
    Kein Auto-Connect!
    """
    global _ACTIVE_CLIENT
    
    if _ACTIVE_CLIENT is None:
        raise ConnectionError("CRITICAL: IBKR Client not initialized. Run session.connect(...) first.")
        
    if not _ACTIVE_CLIENT.is_connected():
        raise ConnectionError("CRITICAL: IBKR Client initialized but disconnected.")
        
    return _ACTIVE_CLIENT

def is_connected() -> bool:
    """Checks if global client is active and connected."""
    global _ACTIVE_CLIENT
    return _ACTIVE_CLIENT is not None and _ACTIVE_CLIENT.is_connected()

def connect(host: str, port: int, client_id: int):
    """
    Stellt die globale Verbindung her.
    Dies ist der EINZIGE Ort, an dem .connect() gerufen werden darf.
    """
    global _ACTIVE_CLIENT
    
    if _ACTIVE_CLIENT and _ACTIVE_CLIENT.is_connected():
        print(f"⚠️ Session already active ({_ACTIVE_CLIENT.host}:{_ACTIVE_CLIENT.port}). Ignoring connect().")
        return

    print(f"🔌 Connecting to IBKR Session ({host}:{port} ID:{client_id})...")
    
    client = IBKRClient(host=host, port=port, client_id=client_id)
    try:
        client.connect()
        # Bei Erfolg setzen wir den Global State
        _ACTIVE_CLIENT = client
        print("✅ Session Established.")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        raise e

def disconnect():
    """Beendet die aktive Session sauber."""
    global _ACTIVE_CLIENT
    if _ACTIVE_CLIENT:
        _ACTIVE_CLIENT.disconnect()
        _ACTIVE_CLIENT = None
        print("🔌 Session Disconnected.")
