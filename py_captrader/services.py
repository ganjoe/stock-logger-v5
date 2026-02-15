# py_captrader/services.py
from typing import Optional, Any
from py_tradeobject.interface import IBrokerAdapter

# Globale Instanz des aktiven Brokers (Service Locator)
_BROKER_INSTANCE: Optional[IBrokerAdapter] = None
_CLI_INSTANCE: Optional[Any] = None

def register_broker(broker: IBrokerAdapter):
    """
    Registriert die globale Broker-Instanz für das System.
    Wird typischerweise beim Start (run_live/run_paper) aufgerufen.
    """
    global _BROKER_INSTANCE
    _BROKER_INSTANCE = broker
    print(f"✅ Broker Registered: {broker.__class__.__name__}")

def get_broker() -> IBrokerAdapter:
    """
    Liefert den registrierten Broker zurück.
    Wirft einen Fehler, wenn kein Broker registriert ist.
    """
    if _BROKER_INSTANCE is None:
        raise RuntimeError("CRITICAL: No Broker Adapter registered. Run system setup first.")
    return _BROKER_INSTANCE

def has_broker() -> bool:
    """Prüft, ob ein Broker verfügbar ist."""
    return _BROKER_INSTANCE is not None

def register_cli(cli: Any):
    """Registriert den aktiven CLI-Controller."""
    global _CLI_INSTANCE
    _CLI_INSTANCE = cli

def get_cli() -> Any:
    """Liefert den registrierten CLI-Controller."""
    if _CLI_INSTANCE is None:
        raise RuntimeError("CLI Controller not registered.")
    return _CLI_INSTANCE
