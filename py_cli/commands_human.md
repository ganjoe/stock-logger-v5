# CLI Commands - Human Mode

Dies ist die Referenz für den menschlichen Operator. Diese Befehle dienen primär der Visualisierung und Kontrolle.

## System Commands

### `user <human|pta>`
Schaltet den Betriebsmodus um.
- `user human`: Aktiviert **Pretty Print** (lesbare Tabellen, Emojis).
- `user pta`: Aktiviert den **Bot Mode** (JSON Output).

## Monitoring (Read-Only)

### `status`
Zeigt einen Live-Snapshot des Portfolios.
- **Output**: Equity, Cash, Offene Positionen, Unrealized PnL.
- **Quelle**: Live-Daten vom Broker.

### `trades`
Listet alle aktiven Positionen/Trades auf.

### `history [tage]`
Zeigt den Portfolio-Stand in der Vergangenheit (End-Of-Day). Standardmäßig heute (0).

## Trading (Intervention)

⚠️ **Achtung**: Manuelle Eingriffe sollten vermieden werden, wenn der Bot aktiv handelt.

### `trade <json_payload>`
Wrapper für komplexe Trade-Operationen. Siehe `commands_pta.md`.
Im Human-Mode wird empfohlen, diesen Befehl **nicht** manuell zu tippen, da JSON fehleranfällig ist.

### `close <trade_id> --confirm`
Schließt einen Trade manuell. Erfordert die explizite Bestätigung `--confirm`.
