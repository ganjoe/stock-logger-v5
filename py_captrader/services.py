# py_captrader/services.py
from typing import Optional
from py_tradeobject.interface import IBrokerAdapter

# Globale Instanz des aktiven Brokers (Service Locator)
_BROKER_INSTANCE: Optional[IBrokerAdapter] = None

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
