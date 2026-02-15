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

## Trading (Intervention)

⚠️ **Achtung**: Manuelle Eingriffe sollten vermieden werden, wenn der Bot aktiv handelt.

### `trade <json_payload>`
Wrapper für komplexe Trade-Operationen. Siehe `commands_pta.md`.
Im Human-Mode wird empfohlen, diesen Befehl **nicht** manuell zu tippen, da JSON fehleranfällig ist.
