import logging
import asyncio
from ib_insync import IB
import sys

from py_captrader.config import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_CLIENT_ID

# Configure logging to see the handshake process
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Central Config from our updated py_captrader.config
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    client_id = 99 # Keep unique client ID for tests
    
    # [FIX] Ensure we have an active event loop (same logic as in main client)
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

    ib = IB()
    print(f"📡 Testing Connection to IBKR Gateway...")
    print(f"   Target: {host}:{port}")
    print(f"   Client: {client_id}")
    
    try:
        # Reduced timeout for faster debugging
        ib.connect(host, port, clientId=client_id, timeout=15)
        print("✅ SUCCESS: IBKR Gateway connection established!")
        
        # Fetch some basic info to verify data flow
        print(f"   Server Version: {ib.client.serverVersion()}")
        
        ib.disconnect()
        print("🔌 Disconnected cleanly.")
    except Exception as e:
        print(f"❌ FAILURE: Could not connect to IBKR Gateway.")
        print(f"   Error: {type(e).__name__}: {e}")
        print("\n   Tipp: Prüfe ob der Gateway fertig eingeloggt ist (2FA bestätigt?).")
        sys.exit(1)

if __name__ == "__main__":
    main()
