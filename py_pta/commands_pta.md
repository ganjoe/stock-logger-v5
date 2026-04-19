# CLI Commands - PTA Mode (Bot First)

Dies ist die technische Referenz für Bots (Gemini PTA). Alle Antworten sind **JSON**.



## Monitoring

### `status [json_filter]`
Liefert den aktuellen **Live-Snapshot** des Portfolios. Akzeptiert optional ein JSON-Objekt zur Filterung (Token-Ersparnis).

### `market_clock`
Liefert den Status der Börse (NYSE), Zeit bis zum nächsten Event und Zeitstempel.

- **Payload**:
```json
{
  "status": "OPEN",
  "server_time_et": "2026-02-16 10:30:00 EST",
  "next_event": "CLOSE",
  "seconds_to_next_event": 19800,
  "calendar_outdated": false
}
```
- **Zweck**: Timing-Entscheidungen für den Bot (kein Entry im After-Market, Feiertags-Check).

**Beispiel (Gefiltert):**
`status '{"ticker": "AAPL"}'`

- **Payload**: `py_portfolio_state.objects.PortfolioSnapshot`.
- **Inhalt**: Enthält `cash`, `equity` und nur die `positions[]` und `active_orders[]` des Typs **AAPL**.


## Trading (Execution)

### `trade <json_payload>`
Der zentrale Endpoint für alle Handelsaktionen. Parsed das JSON und delegiert an `py_tradeobject`.

#### 1. ENTER (Neuer Trade)

**Limit Order** (mit Preis):
```json
{
  "action": "ENTER",
  "ticker": "AAPL",
  "quantity": 10,
  "limit_price": 150.0,
  "stop_loss": 140.0
}
```

**Market Order** (ohne `limit_price`):
```json
{
  "action": "ENTER",
  "ticker": "AAPL",
  "quantity": 10
}
```
> Wird `limit_price` weggelassen oder auf `null` gesetzt, erzeugt `TradeObject.enter` eine **Market Order**.
> `stop_loss` ist ebenfalls optional.

**Antwort**:
```json
{
  "success": true,
  "payload": {
    "trade_id": "TRD-XXXX",
    "broker_order_id": "9001",
    "status": "OPENING"
  }
}
```

#### 2. UPDATE (Stop Loss / Management)
```json
{
  "action": "UPDATE",
  "ticker": "AAPL",
  "trade_id": "TRD-XXXX",
  "stop_loss": 145.5
}
```

#### 3. EXIT (Close Position)
```json
{
  "action": "EXIT",
  "ticker": "AAPL",
  "trade_id": "TRD-XXXX"
}
```

#### 4. CANCEL (Order Löschen)
Löscht eine spezifische, aktive Order (z.B. einen nicht ausgeführten Entry).
```json
{
  "action": "CANCEL",
  "trade_id": "TRD-XXXX",
  "ticker": "AAPL",
  "broker_order_id": "9001"
}
```

#### 5. REFRESH (Force Sync)
```json
{
  "action": "REFRESH",
  "trade_id": "TRD-XXXX",
  "ticker": "AAPL"
}
```
**Effekt**: Zwingt das TradeObject, Updates vom Broker zu laden (Fills, Status).

#### 6. CASH (Ein/Auszahlungen)
Regel: Positive quantity = Einzahlung, Negative quantity = Auszahlung.
```json
{
  "action": "CASH",
  "quantity": 5000,
  "note": "Initial Funding"
}
```

### `quote SYMBOL`
Liefert den aktuellen Marktpreis eines Symbols.
- **Rückgabe**: `{"success": true, "payload": {"ticker": "SYMBOL", "price": 123.45}}`

### `history [days_back]`
Liefert einen historischen Portfolio-Snapshot.
- **Payload**: `py_portfolio_state.objects.PortfolioSnapshot` zum Zielzeitpunkt.
- **Standard**: `days_back=0` (heute).

### `trades`
Listenansicht aller offenen Positionen.
- **Rückgabe**: `{"success": true, "payload": {"trades": [...]}}`

### `close <trade_id> [--confirm]`
Schließt einen Trade explizit. 
- **Sicherheits-Check**: In PTA Mode ist `--confirm` oder `--force` zwingend erforderlich, sofern nicht `confirm_all` im Kontext gesetzt ist.

### `analyze [live|history] [json_payload]`
Führt Analysen auf Live- oder Historiendaten aus.

#### 1. LIVE Analysis
Analysiert den aktuellen Stand (Risk, Heat, Alerts).
`analyze live '{"ticker": "AAPL"}'` (optionaler Ticker-Filter)

- **Payload**: `py_riskmanager.models.AnalyticsReport` (DTO). Enthält berechnete Risiko-Metriken und Tabellen-Daten.
#### 2. HISTORY Analysis


## System Control

### `connect [host|default] [port] [client_id]` 
Verbindet den Bot mit dem IBKR Gateway.
- **host**: IP Adresse des Gateways (Standard: 127.0.0.1).
- **port**: Port (Standard: 4001).
- **client_id**: Eindeutige ID (Standard: 1).
- **Automatisches Trennen**: Bestehende Verbindungen werden automatisch getrennt, falls eine Verbindung zu einem anderen Target (IP/Port) angefordert wird.
- **Rückgabe**: `{"success": true, "message": "Connected to 127.0.0.1:4001 (ID: 1)"}`

### `disconnect`
Trennt die Verbindung.
- **Rückgabe**: `{"success": true}`

## Special Codewords

### `Risk Check`
Triggered durch User-Eingabe "Risk Check" oder "Wie hoch ist mein Risiko?".
- **Aktion**: Bot führt intern `analyze live` aus.
- **Antwort**: "Current Heat: 2.5% (3299 €). Trades without Stop: MSFT, TSLA"

### `wizard <json_payload>`
Berechnet die optimale Positionsgröße nach Minervini-Regeln 

- **Payload (Request)**:
```json
{
  "symbol": "NVDA",
  "entry": 100.0,
  "stop": 95.0,
  "risk_pct": 1.0,        // Optional (Default 1.0)
  "max_pos_pct": 25.0,    // Optional (Default 25.0)
  "equity_override": 100000.0 // Optional (sonst Live-Broker)
}
```

- **Rückgabe**:
```json
{
  "success": true,
  "payload": {
    "symbol": "NVDA",
    "suggested_shares": 500,
    "bottleneck": "RISK",
    "risk_amount": 2500.0,
    "scenarios": {
      "breakeven": 100.2,
      "target_2r": 110.0
    },
    "warnings": []
  }
}
```
