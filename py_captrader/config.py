import os

# IBKR Gateway Docker Connection
# Default verweist auf den Docker DNS-Namen (transparent für Live/Paper durch die Docker Umgebung)
GATEWAY_HOST = os.getenv("IB_GATEWAY_HOST", "ib-gateway_live-ib-gateway-1")
GATEWAY_PORT = int(os.getenv("IB_GATEWAY_PORT", "4001"))

# CLIENT ID (Standard)
DEFAULT_CLIENT_ID = 22

# Current Defaults
DEFAULT_HOST = GATEWAY_HOST
DEFAULT_PORT = GATEWAY_PORT
