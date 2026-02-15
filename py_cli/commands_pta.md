# CLI Commands - PTA Mode (Bot First)

Dies ist die technische Referenz für Bots (Gemini PTA). Alle Antworten sind **JSON**.

## System Control

### `user pta | user human`
Modus-Wahl.
- **Rückgabe**: `{"success": true, "payload": {"mode": "BOT", ...}}`

## Monitoring

### `status`
Liefert den aktuellen **Live-Snapshot** des Portfolios direkt vom Broker.
- **Payload**: `py_portfolio_state.objects.PortfolioSnapshot` als `dict`.
- **Inhalt**: Enthält `cash`, `equity`, `positions[]` und **alle** aktuell beim Broker offenen `active_orders[]`.
- **Zweck**: Primäre Datenquelle für den Bot, um den Ist-Zustand (inklusive hängender Orders) zu prüfen.

## Trading (Execution)

### `trade <json_payload>`
Der zentrale Endpoint für alle Handelsaktionen. Parsed das JSON und delegiert an `py_tradeobject`.

#### 1. ENTER (Neuer Trade)
```json
{
  "action": "ENTER",
  "ticker": "AAPL",
  "quantity": 10,
  "limit_price": 150.0,
  "stop_loss": 140.0
}
```
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
  "trade_id": "TRD-XXXX",
  "stop_loss": 145.5
}
```

#### 3. EXIT (Close Position)
```json
{
  "action": "EXIT",
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
