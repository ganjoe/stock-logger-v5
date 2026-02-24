#!/usr/bin/env python3
"""
trades_import.py
================
Importiert Trades aus der Legacy-Datei 'trades.xml' in TradeObject JSON-Dateien.

Logik:
1. Parst alle <Trade> Elemente aus trades.xml
2. Gruppiert Executions nach Symbol (Ticker)
3. Für jeden Ticker:
   a) Prüft ob bereits TradeObjects in ./data/trades/{TICKER}/ existieren
   b) Falls ja: Prüft ob Merge nötig (neue Transaktionen hinzufügen)
   c) Falls nein: Erstellt neues TradeObject
4. Notes = "legacy", Stop Loss = 0

Besonderheiten:
- Deutsche Zahlenformate (Komma statt Punkt): "122,50" -> 122.50
- Commission ist negativ in der XML, wird als abs() gespeichert
- Quantity ist signed: + = Buy, - = Sell
"""
import os
import sys
import json
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from py_tradeobject.models import (
    TradeState, TradeStatus, TradeType,
    TradeTransaction, TransactionType
)


# --- Config ---
XML_PATH = os.path.join(os.path.dirname(__file__), "trades.xml")
TRADES_DIR = os.path.join(os.path.dirname(__file__), "data", "trades")
DRY_RUN = "--dry-run" in sys.argv


# --- Helpers ---

def parse_german_float(value: str) -> float:
    """Converts German decimal format '1.234,56' to float 1234.56"""
    # Remove thousands separator (dot), replace decimal comma with dot
    return float(value.replace(".", "").replace(",", "."))


def parse_german_date(date_str: str, time_str: str) -> datetime:
    """Parses 'DD.MM.YYYY' + 'HH:MM:SS' into datetime."""
    return datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M:%S")


@dataclass
class LegacyExecution:
    """Parsed execution from trades.xml"""
    xml_id: str           # Original MD5 hash ID from XML
    symbol: str
    name: str
    isin: str
    currency: str
    timestamp: datetime
    quantity: float       # Signed: + buy, - sell
    price: float
    commission: float     # Always positive (abs of XML value)
    proceeds: float


def parse_xml(xml_path: str) -> List[LegacyExecution]:
    """Parses all <Trade> elements from trades.xml"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    executions = []
    trades_elem = root.find("Trades")
    if trades_elem is None:
        print("  [WARN] No <Trades> section found in XML.")
        return executions

    for trade_elem in trades_elem.findall("Trade"):
        try:
            xml_id = trade_elem.get("id", "")
            name = trade_elem.get("name", "")
            isin = trade_elem.get("isin", "")

            # Meta
            meta = trade_elem.find("Meta")
            date_str = meta.find("Date").text
            time_str = meta.find("Time").text
            timestamp = parse_german_date(date_str, time_str)

            # Instrument
            instrument = trade_elem.find("Instrument")
            symbol = instrument.find("Symbol").text
            currency = instrument.find("Currency").text

            # Execution
            execution = trade_elem.find("Execution")
            quantity = parse_german_float(execution.find("Quantity").text)
            price = parse_german_float(execution.find("Price").text)
            commission = abs(parse_german_float(execution.find("Commission").text))
            proceeds = parse_german_float(execution.find("Proceeds").text)

            executions.append(LegacyExecution(
                xml_id=xml_id,
                symbol=symbol,
                name=name,
                isin=isin,
                currency=currency,
                timestamp=timestamp,
                quantity=quantity,
                price=price,
                commission=commission,
                proceeds=proceeds
            ))
        except Exception as e:
            print(f"  [ERROR] Failed to parse trade element: {e}")
            continue

    return executions


def group_into_trades(executions: List[LegacyExecution]) -> Dict[str, List[List[LegacyExecution]]]:
    """
    Groups executions by symbol, then splits into logical trades.

    A logical trade = sequence of executions where net position goes from 0 -> non-zero -> 0.
    If net position never returns to 0, the entire sequence is one open trade.
    """
    # Step 1: Group by symbol and sort by time
    by_symbol: Dict[str, List[LegacyExecution]] = defaultdict(list)
    for ex in executions:
        by_symbol[ex.symbol].append(ex)

    for sym in by_symbol:
        by_symbol[sym].sort(key=lambda x: x.timestamp)

    # Step 2: Split each symbol's executions into logical trades
    result: Dict[str, List[List[LegacyExecution]]] = {}

    for symbol, execs in by_symbol.items():
        trades: List[List[LegacyExecution]] = []
        current_trade: List[LegacyExecution] = []
        net_qty = 0.0

        for ex in execs:
            current_trade.append(ex)
            net_qty += ex.quantity

            # If net quantity returns to zero, this logical trade is complete
            if abs(net_qty) < 0.0001:
                trades.append(current_trade)
                current_trade = []
                net_qty = 0.0

        # If there's an open trade remaining
        if current_trade:
            trades.append(current_trade)

        result[symbol] = trades

    return result


def load_existing_trades(ticker: str) -> List[Tuple[str, TradeState]]:
    """Loads all existing TradeObject JSONs for a ticker. Returns [(filepath, state)]."""
    ticker_dir = os.path.join(TRADES_DIR, ticker)
    if not os.path.exists(ticker_dir):
        return []

    results = []
    for filename in os.listdir(ticker_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(ticker_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                state = TradeState.from_dict(data)
                results.append((filepath, state))
        except Exception as e:
            print(f"  [WARN] Could not load {filepath}: {e}")
    return results


def get_existing_tx_timestamps(state: TradeState) -> set:
    """Returns set of transaction timestamps (as ISO strings) for duplicate detection."""
    return {tx.timestamp.isoformat() for tx in state.transactions}


def executions_to_transactions(execs: List[LegacyExecution]) -> List[TradeTransaction]:
    """Converts legacy executions to TradeTransaction objects."""
    transactions = []
    net_qty = 0.0

    for ex in execs:
        # Determine transaction type
        if net_qty == 0 or (net_qty > 0 and ex.quantity > 0) or (net_qty < 0 and ex.quantity < 0):
            tx_type = TransactionType.ENTRY
        else:
            tx_type = TransactionType.EXIT

        net_qty += ex.quantity

        transactions.append(TradeTransaction(
            id=ex.xml_id[:8],  # Use first 8 chars of XML hash as ID
            timestamp=ex.timestamp,
            type=tx_type,
            quantity=ex.quantity,
            price=ex.price,
            commission=ex.commission,
            slippage=0.0,
            order_id=None
        ))

    return transactions


def determine_status(transactions: List[TradeTransaction]) -> TradeStatus:
    """Determines trade status based on net quantity."""
    net_qty = sum(tx.quantity for tx in transactions)
    if abs(net_qty) < 0.0001:
        return TradeStatus.CLOSED
    return TradeStatus.OPEN


def create_trade_state(ticker: str, transactions: List[TradeTransaction],
                       name: str = "", isin: str = "",
                       currency: str = "USD") -> TradeState:
    """Creates a new TradeState from transactions."""
    trade_id = str(uuid.uuid4())
    status = determine_status(transactions)

    note_parts = ["legacy"]
    if name:
        note_parts.append(name)
    if isin:
        note_parts.append(f"ISIN:{isin}")

    return TradeState(
        id=trade_id,
        ticker=ticker,
        status=status,
        trade_type=TradeType.STOCK,
        transactions=transactions,
        initial_stop_price=0,  # Missing stop losses -> 0
        current_stop_price=0 if status == TradeStatus.OPEN else None,
        entry_date=transactions[0].timestamp if transactions else None,
        notes=" | ".join(note_parts),
        currency=currency
    )


def save_trade_state(state: TradeState) -> str:
    """Saves TradeState as JSON file. Returns filepath."""
    ticker_dir = os.path.join(TRADES_DIR, state.ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    filepath = os.path.join(ticker_dir, f"{state.id}.json")
    data = state.to_dict()

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    return filepath


def try_merge(existing: List[Tuple[str, TradeState]],
              new_transactions: List[TradeTransaction],
              ticker: str) -> Optional[str]:
    """
    Checks if new transactions should be merged into an existing TradeObject.
    Returns the filepath if merged, None otherwise.

    Merge criteria: At least one new transaction timestamp matches
    an existing transaction timestamp (duplicate detection).
    If duplicates found, only add truly new transactions.
    """
    new_timestamps = {tx.timestamp.isoformat() for tx in new_transactions}

    for filepath, state in existing:
        existing_timestamps = get_existing_tx_timestamps(state)

        # Check for overlap
        overlap = new_timestamps & existing_timestamps
        if overlap:
            # Merge: Add only non-duplicate transactions
            truly_new = [tx for tx in new_transactions
                         if tx.timestamp.isoformat() not in existing_timestamps]

            if not truly_new:
                return filepath  # All already present, skip

            state.transactions.extend(truly_new)
            state.transactions.sort(key=lambda t: t.timestamp)
            state.status = determine_status(state.transactions)

            if "legacy" not in state.notes:
                state.notes = f"legacy | {state.notes}" if state.notes else "legacy"

            # Re-save
            data = state.to_dict()
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            return filepath

    return None


# --- Main ---

def main():
    print("=" * 60)
    print("  trades_import.py – Legacy XML → TradeObject Converter")
    print("=" * 60)

    if DRY_RUN:
        print("  🔍 DRY RUN MODE – No files will be written.\n")

    # 1. Parse XML
    print(f"\n  📖 Parsing {XML_PATH}...")
    executions = parse_xml(XML_PATH)
    print(f"     Found {len(executions)} executions.")

    # 2. Group into logical trades
    grouped = group_into_trades(executions)
    total_trades = sum(len(trades) for trades in grouped.values())
    print(f"     Grouped into {total_trades} logical trades across {len(grouped)} symbols.\n")

    # 3. Process each symbol
    stats = {"created": 0, "merged": 0, "skipped": 0, "errors": 0}

    for symbol in sorted(grouped.keys()):
        trade_groups = grouped[symbol]
        existing = load_existing_trades(symbol)

        print(f"  📊 {symbol}: {len(trade_groups)} trade(s), "
              f"{len(existing)} existing TradeObject(s)")

        for i, execs in enumerate(trade_groups):
            # Get metadata from first execution
            first = execs[0]
            transactions = executions_to_transactions(execs)

            # Try merge with existing
            if existing:
                merged_path = try_merge(existing, transactions, symbol)
                if merged_path:
                    if DRY_RUN:
                        print(f"     [DRY] Would merge trade #{i+1} into {os.path.basename(merged_path)}")
                    else:
                        print(f"     ✅ Merged trade #{i+1} into {os.path.basename(merged_path)}")
                    stats["merged"] += 1
                    continue

            # Create new TradeObject
            state = create_trade_state(
                ticker=symbol,
                transactions=transactions,
                name=first.name,
                isin=first.isin,
                currency=first.currency
            )

            net_qty = sum(tx.quantity for tx in transactions)
            status_icon = "🟢" if abs(net_qty) > 0.0001 else "⚪"

            if DRY_RUN:
                print(f"     [DRY] Would create {status_icon} "
                      f"{state.status.value} ({len(transactions)} fills, "
                      f"net={net_qty:+.0f})")
            else:
                try:
                    filepath = save_trade_state(state)
                    print(f"     ✅ Created {status_icon} {os.path.basename(filepath)} "
                          f"({state.status.value}, {len(transactions)} fills, "
                          f"net={net_qty:+.0f})")
                    stats["created"] += 1
                except Exception as e:
                    print(f"     ❌ Error saving: {e}")
                    stats["errors"] += 1

    # 4. Summary
    print(f"\n{'=' * 60}")
    print(f"  Summary:")
    print(f"    Created:  {stats['created']}")
    print(f"    Merged:   {stats['merged']}")
    print(f"    Skipped:  {stats['skipped']}")
    print(f"    Errors:   {stats['errors']}")
    print(f"{'=' * 60}")

    if DRY_RUN:
        print("\n  ⚠️  This was a DRY RUN. Run without --dry-run to actually import.")


if __name__ == "__main__":
    main()
