import logging
from ib_insync import IB
import sys

from py_captrader.config import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_CLIENT_ID

# Configure logging to see the handshake process
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Central Config
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    client_id = 99 # Keep unique client ID for tests
    
    ib = IB()
    print(f"Attempting to connect to {host}:{port} (ClientID: {client_id})...")
    
    try:
        # Reduced timeout for faster debugging of logs
        ib.connect(host, port, clientId=client_id, timeout=10)
        print("✅ SUCCESS: Connected to IBKR Gateway!")
        ib.disconnect()
    except Exception as e:
        print(f"❌ FAILURE: Could not connect to IBKR Gateway.")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
