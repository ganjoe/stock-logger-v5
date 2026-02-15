# ALM Prinzipien - Architektur & Design

Dieses Dokument beschreibt die fundamentalen Prinzipien der Systemarchitektur, die strikt eingehalten werden müssen.

## 1. Verbindungsmanagement (Connection Management & Broker Services)

### Grundsatz: Explizite Verbindungsherstellung
Das System stellt **niemals** automatisch eine Verbindung zu externen Diensten (Broker, Datenbanken) her ("Auto-Connect"). Eine Verbindung muss immer explizit durch eine dedizierte Start-Routine initiiert werden.

### Umsetzung
*   **Modul**: `py_captrader` ist der alleinige Eigentümer ("Owner") der IBKR-Verbindung **und** des Broker-Services.
*   **Session**: Es gibt genau ein globales Session-Objekt (Singleton-Pattern), das den aktiven `IBKRClient` hält (`py_captrader.session`).
*   **Service Locator**: Der `IBrokerAdapter` (Domain-Schicht) wird global über `py_captrader.services` zur Verfügung gestellt.
    *   `register_broker(adapter)`: Registriert die Instanz beim Start (`run_live.py`).
    *   `get_broker()`: Liefert die Instanz an Verbraucher (`py_tradeobject`, `py_market_data`).
*   **Verbraucher**: Andere Module rufen niemals `Client(host=...)` auf. Sie fordern den Broker via `services.get_broker()` an.
*   **Fehlerverhalten**: Ist kein Broker/Client aktiv, stürzt der Aufruf sofort ab (`RuntimeError` / `ConnectionError`).

### Entry Points
Für den Start der Anwendung gibt es spezifische Root-Skripte, die die Verbindungsparameter fix definieren:
*   `run_paper.py`: Startet Paper-Trading (Port 4002, ID 0) -> Registriert `CapTraderAdapter`.
*   `run_live.py`: Startet Live-Trading (Port 4001, ID 0) -> Registriert `CapTraderAdapter`.

## 2. Bot-First Principle (Interface Design)

### Grundsatz: Daten vor Darstellung
Jede Schnittstelle (API, CLI-Command, Modul-Output) ist primär für die maschinelle Verarbeitung (durch Bots/KI) ausgelegt. Menschliche Lesbarkeit ("Human Mode") ist lediglich eine sekundäre Transformation (Render-Layer) der strukturierten Daten.

### Umsetzung
*   **CommandResponse**: Der Rückgabewert eines jeden Befehls enthält zwingend ein strukturiertes Datenobjekt (`payload` / `data` als Dict).
*   **Kein String-Parsing**: Bots oder aufrufende Module müssen niemals Textstrings parsen ("Success: Trade created"). Sie verlassen sich ausschließlich auf Boolesche Flags (`success`) und Datenfelder (`payload.trade_id`).
*   **JSON-Wrapper**: Komplexe Befehle werden nicht über endlos viele CLI-Argumente abgebildet, sondern akzeptieren ein JSON-Payload als einziges Argument.
*   **Rendering**: Die Umwandlung in menschenlesbaren Text (Tabellen, Emojis, Sätze) erfolgt erst im letzten Schritt (`CLIController`), falls der `HUMAN` Modus aktiv ist. Sie darf die zugrundeliegende Datenstruktur nicht beeinflussen.
*   **Strikt getrennte Kanäle**: 
    *   **Stdout** ist exklusiv für strukturierte Daten (JSON) reserviert. Der Bot sieht hierdurch immer nur sauberes JSON auf dem Hauptkanal.
    *   **Stderr** wird für alle Log-Ausgaben, Warnungen und Fehlermeldungen genutzt. Der Entwickler (oder das Log-File) sieht die Fehlermeldungen trotzdem noch im Terminal, ohne dass der Datenfluss gestört wird.

