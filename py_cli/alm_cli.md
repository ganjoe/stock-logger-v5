# ALM – py_cli (Command Line Interface)

| ID | Category | Title | Description | Status | Covered By |
|----|----------|-------|-------------|--------|------------|
| F-ARC-010 | Architecture | Unified Gateway Core | CLI dient als einziger Entry-Point für Mensch und Bot. | DONE | `main_cli.py` |
| F-ARC-020 | Architecture | Logic Decoupling | CLI rein als I/O Layer ohne Geschäftslogik. | DONE | `py_cli` logic delegation |
| F-SEC-010 | Session | Explicit Session Modes | Headless/Bot Modus via `--mode=bot` Fixierung. | DONE | `main_cli.py` |
| F-SEC-020 | Safety | Action Confirmation Protocol | Bestätigung via `--confirm` im Bot-Mode zwingend. | DONE | `handlers_execution.py` |
| F-SEC-030 | Security | Actor Audit Trail | Zuordnung Akteur im Log (Human vs Bot). | DONE | `TradeOrderLog` |
| F-INT-010 | Interface | Context-Aware Rendering | Rendering als Text (Human) oder JSON (Bot). | DONE | `controller.py` |
| F-INT-020 | Interface | Structured Error Protocol | Fehler als JSON mit `error_code` und `message`. | DONE | `models.py` |
| F-LOG-010 | Logic | Trade Object Encapsulation | Manipulationen nur via TradeObject. Keine Direkt-Orders. | DONE | `handlers_trade.py` |
| F-DAT-010 | Data | One-to-Many View Association | ID-Referenzierung über TradeObject (UUID). | DONE | `TradeObject.from_dict` |
| F-DAT-020 | Data | Bulk Data Fetch | Hintergrund-Download historischer Marktdaten via `bulk_fetch`. | DONE | `handlers_analytics.py` |
| F-DAT-030 | Data | Portfolio History | Befehl `history` zur Anzeige historischer Portfolio-Snapshots. | DONE | `handlers_history.py` |
| F-UX-010 | Visualization | ID-First Display Strategy | Trade-ID zwingend in der ersten Spalte. | DONE | `handlers_monitor.py` |
| F-CLI-030 | Efficiency | Server-Side Filtering | Status-Abfrage erlaubt JSON-Filter zur Token-Ersparnis. | DONE | `handlers_monitor.py` |
| F-CLI-040 | Interface | Analytics Integration | Befehl `analyze` zur Risikoprüfung via CLI verfügbar. | DONE | `handlers_analytics.py` |
| F-CON-010 | Connection | Broker Connection Management | Befehle `connect` / `disconnect` zur Broker-Anbindung. | DONE | `handlers_connection.py` |
| F-MON-010 | Monitoring | Live Quote | Befehl `quote SYMBOL` liefert aktuellen Marktpreis. | DONE | `handlers_monitor.py` |
| F-MON-020 | Monitoring | Market Clock | Befehl `market_clock` liefert Börsenstatus und Zeitinfo. | DONE | `handlers_analytics.py` |
| F-VIS-010 | Visualization | Dashboard Management | Befehle `dashboard --start/--stop/--clear` zur Server-Steuerung und Datenpush. | DONE | `handlers_dashboard.py` |
| F-VIS-020 | Visualization | Chart Data Piping | Flag `--to-dashboard` piped Chart-Daten direkt ans Dashboard (kein Context-Bloat). | DONE | `handlers_monitor.py` |
| F-VIS-030 | Visualization | Candlestick Charts | Flag `--candle` sendet OHLC-Daten für Candlestick-Darstellung im Dashboard. | DONE | `handlers_monitor.py`, `index.html` |
| F-PTA-010 | Integration | PTA Bot Integration | Befehle `pta` und `chat` zur Interaktion mit dem Gemini Personal Trading Assistant. | DONE | `handlers_pta.py` |
| F-TRD-010 | Trading | Position Sizing Wizard | Befehl `wizard` berechnet Positionsgröße nach Minervini-Regeln. | DONE | `handlers_analytics.py` |
| F-TRD-020 | Trading | Market Order Support | ENTER ohne `limit_price` erzeugt eine Market Order (statt Limit Order). | DONE | `handlers_trade.py` |
| F-TRD-030 | Trading | Order Cancellation | CANCEL-Action löscht eine spezifische, aktive Broker-Order. | DONE | `handlers_trade.py` |
| F-INT-030 | Integration | Matrix Chat Interface | PTA erreichbar über Matrix Chat Room via `py_matrix` und `main_matrix.py`. | DONE | `py_matrix/bot.py` |
| F-API-010 | API | Capability Discovery | Befehl `capabilities` zur Feature Negotiation. | PENDING | – |
