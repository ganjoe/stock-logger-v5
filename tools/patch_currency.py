#!/usr/bin/env python3
"""
patch_currency.py
=================
One-time patch: Adds 'currency' field to already-imported legacy TradeObject JSONs.
Reads currency per ticker from trades.xml, patches all JSON files in data/trades/.

Usage:
    python tools/patch_currency.py --dry-run   # Preview only
    python tools/patch_currency.py              # Patch files
"""
import os
import sys
import json
import xml.etree.ElementTree as ET
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_PATH = os.path.join(BASE_DIR, "trades.xml")
TRADES_DIR = os.path.join(BASE_DIR, "..", "data", "trades")
DRY_RUN = "--dry-run" in sys.argv


def extract_currencies_from_xml(xml_path: str) -> dict:
    """Returns {SYMBOL: CURRENCY} from trades.xml."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    currencies = {}

    trades_elem = root.find("Trades")
    if trades_elem is None:
        return currencies

    for trade_elem in trades_elem.findall("Trade"):
        instrument = trade_elem.find("Instrument")
        if instrument is None:
            continue
        symbol = instrument.find("Symbol").text
        currency = instrument.find("Currency").text
        currencies[symbol] = currency

    return currencies


def main():
    print("=" * 60)
    print("  patch_currency.py – Add currency to TradeObject JSONs")
    print("=" * 60)

    if DRY_RUN:
        print("  🔍 DRY RUN MODE – No files will be modified.\n")

    # 1. Extract currencies from XML
    print(f"  📖 Reading {XML_PATH}...")
    currencies = extract_currencies_from_xml(XML_PATH)
    non_usd = {k: v for k, v in currencies.items() if v != "USD"}
    print(f"     Found {len(currencies)} tickers, {len(non_usd)} non-USD: "
          f"{', '.join(f'{k}={v}' for k, v in sorted(non_usd.items()))}\n")

    # 2. Walk all trade JSONs
    trades_dir = os.path.normpath(TRADES_DIR)
    stats = {"patched": 0, "already_set": 0, "no_xml_data": 0, "errors": 0}

    for ticker in sorted(os.listdir(trades_dir)):
        ticker_dir = os.path.join(trades_dir, ticker)
        if not os.path.isdir(ticker_dir):
            continue

        currency = currencies.get(ticker)
        if currency is None:
            # Not a legacy ticker (e.g. created by PTA)
            continue

        for fname in sorted(os.listdir(ticker_dir)):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(ticker_dir, fname)

            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                existing = data.get("currency")
                if existing and existing != "USD":
                    stats["already_set"] += 1
                    continue

                # Patch: add/update currency, add exchange=""
                data["currency"] = currency
                if "exchange" not in data:
                    data["exchange"] = ""

                if DRY_RUN:
                    if currency != "USD":
                        print(f"  [DRY] {ticker}/{fname}: would set currency={currency}")
                else:
                    with open(filepath, "w") as f:
                        json.dump(data, f, indent=2)
                    if currency != "USD":
                        print(f"  ✅ {ticker}/{fname}: currency={currency}")

                stats["patched"] += 1

            except Exception as e:
                print(f"  ❌ {ticker}/{fname}: {e}")
                stats["errors"] += 1

    # 3. Summary
    print(f"\n{'=' * 60}")
    print(f"  Summary:")
    print(f"    Patched:      {stats['patched']}")
    print(f"    Already set:  {stats['already_set']}")
    print(f"    Errors:       {stats['errors']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
