import os
import glob
import csv
import hashlib
import argparse
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import json

"""
###############################################################################
# IB CSV Converter (Docker-Ready)
# Unified for stock-logger-v5 context.
###############################################################################
"""

# Path configuration for Docker environment
XML_FILE = "/app/trades.xml"
TICKER_MAP_FILE = "/app/data/ticker_map.json"
OLD_CSV_DIR = "/app/data/old_csv"

def get_file_path():
    """CLI argument parsing & Auto-discovery."""
    parser = argparse.ArgumentParser(description="IB CSV Converter - Import IBKR CSV")
    parser.add_argument("file", nargs="?", help="Path to IBKR/CapTrader CSV file")
    args = parser.parse_args()
    
    ACCOUNT_ID_PREFIX = "U16537315"

    if args.file:
        if not os.path.basename(args.file).startswith(ACCOUNT_ID_PREFIX):
            print(f"-> [TC-150] Error: Invalid filename. Must start with '{ACCOUNT_ID_PREFIX}'.")
            return None
        print(f"-> [TC-010] Explicit file provided: {args.file}")
        return args.file
    
    # Find the newest file in the root directory matching the prefix
    # When running in Docker, this is usually /app/
    all_csvs = glob.glob(f"{ACCOUNT_ID_PREFIX}*.csv")
    if not all_csvs:
        print(f"Error: No valid CSV files (starting with '{ACCOUNT_ID_PREFIX}') found in current directory.")
        return None

    newest_file = max(all_csvs, key=os.path.getmtime)
    print(f"-> [TC-015] Auto-discovered newest file: {newest_file}")
    return newest_file

def to_german_number(value):
    """Convert number to German format (comma decimal)."""
    if not value: return "0,00"
    try:
        clean_val = float(str(value).replace(",", ""))
        return f"{clean_val:.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return str(value)

def generate_hash(data_string):
    """Generate deterministic MD5 hash."""
    return hashlib.md5(data_string.encode("utf-8")).hexdigest()

def parse_date_time(raw_date_time):
    """Split Date/Time and format Date to TT.MM.JJJJ."""
    try:
        raw_date_time = raw_date_time.strip()
        if "," in raw_date_time:
            d_part, t_part = raw_date_time.split(",", 1)
        else:
            d_part, t_part = raw_date_time, "00:00:00"
        
        dt_obj = datetime.strptime(d_part.strip(), "%Y-%m-%d")
        return dt_obj.strftime("%d.%m.%Y"), t_part.strip()
    except Exception:
        return raw_date_time, "00:00:00"

def load_existing_ids(root):
    """Load existing IDs for deduplication."""
    if root is None: return set()
    return {elem.get("id") for elem in root.findall(".//*[@id]")}


def extract_symbol_from_desc(desc):
    """Extracts symbol from description strings."""
    if "(" in desc:
        return desc.split("(", 1)[0].strip()
    return desc.split(" ", 1)[0].strip()

def process_csv(filepath, existing_ids, ticker_map):
    """Main parser logic for GERMAN CapTrader CSVs."""
    new_trades, new_divs, new_deposits = [], [], []
    instrument_metadata = {}
    
    SECTION_TRADES = "Transaktionen"
    SECTION_DIVIDENDS = "Dividenden"
    SECTION_DEPOSITS = "Einzahlungen & Auszahlungen"
    SECTION_INFO = "Informationen zum Finanzinstrument"

    with open(filepath, "r", encoding="utf-8-sig") as f:
        all_rows = list(csv.reader(f))

    # --- PASS 1: Metadata (Informationen zum Finanzinstrument) ---
    current_section, headers = None, {}
    token_alias_map = {} 

    for row in all_rows:
        if not row or len(row) < 2: continue
        section_name, row_type = row[0].strip(), row[1].strip()

        if row_type == "Header":
            current_section = section_name
            headers = {name.strip(): idx for idx, name in enumerate(row)}
            continue

        if row_type == "Data" and current_section == SECTION_INFO:
            try:
                sym_raw = row[headers["Symbol"]]
                name = row[headers["Beschreibung"]]
                isin = row[headers["Wertpapier-ID"]]
                
                symbols = [s.strip() for s in sym_raw.split(",")]
                primary_sym = symbols[0]

                for s in symbols:
                    if s != primary_sym:
                        token_alias_map[s] = primary_sym
                
                mapped_primary = ticker_map.get(primary_sym, primary_sym)
                instrument_metadata[mapped_primary] = {"name": name, "id": isin}

            except (KeyError, IndexError):
                continue
                
    if token_alias_map:
        print(f"-> [F-295] Auto-discovered {len(token_alias_map)} ticker aliases from CSV.")

    # --- PASS 2: Transactions (Trades, Divs, Deposits) ---
    current_section, headers = None, {}
    for row in all_rows:
        if not row or len(row) < 2: continue
        section_name, row_type = row[0].strip(), row[1].strip()

        if row_type == "Header":
            current_section = section_name
            headers = {name.strip(): idx for idx, name in enumerate(row)}
            continue

        if row_type == "Data" and current_section:
            if current_section == SECTION_INFO: continue

            if current_section == SECTION_TRADES:
                try:
                    sym = row[headers["Symbol"]]
                    original_sym = sym
                    
                    sym_after_alias = token_alias_map.get(sym, sym)
                    final_sym = ticker_map.get(sym_after_alias, sym_after_alias)
                    
                    if original_sym != final_sym:
                         if sym_after_alias != final_sym:
                              print(f"-> [TC-070] Mapped trade: {sym_after_alias} -> {final_sym}")

                    sym = final_sym 

                    raw_date = row[headers["Datum/Zeit"]]
                    qty = row[headers["Menge"]]
                    proceeds = row[headers["Erlös"]]
                    commission = row[headers["Prov./Gebühr"]]
                    
                    trade_id = generate_hash(f"{raw_date}{original_sym}{qty}{proceeds}{commission}")
                    if trade_id in existing_ids: continue

                    date_fmt, time_fmt = parse_date_time(raw_date)
                    
                    new_trades.append({
                        "id": trade_id, "date": date_fmt, "time": time_fmt,
                        "symbol": sym, "currency": row[headers["Währung"]],
                        "qty": to_german_number(qty),
                        "price": to_german_number(row[headers["T.-Kurs"]]),
                        "commission": to_german_number(commission),
                        "proceeds": to_german_number(proceeds)
                    })
                    existing_ids.add(trade_id)
                except (KeyError, IndexError): continue

            elif current_section == SECTION_DIVIDENDS:
                try:
                    if any("Gesamt" in col for col in row): continue
                    desc = row[headers["Beschreibung"]]
                    sym = extract_symbol_from_desc(desc)
                    original_sym = sym
                    sym_alias = token_alias_map.get(sym, sym)
                    final_sym = ticker_map.get(sym_alias, sym_alias)
                    sym = final_sym

                    if original_sym != sym:
                        print(f"-> [TC-070] Mapped dividend: {original_sym} -> {sym}")
                    
                    raw_date = row[headers["Datum"]]
                    amount = row[headers["Betrag"]]
                    
                    div_id = generate_hash(f"{raw_date}{original_sym}{amount}{desc}")
                    if div_id in existing_ids: continue

                    date_fmt, _ = parse_date_time(raw_date)
                    new_divs.append({
                        "id": div_id, "date": date_fmt, "symbol": sym, 
                        "amount": to_german_number(amount),
                        "currency": row[headers["Währung"]], "desc": desc
                    })
                    existing_ids.add(div_id)
                except (KeyError, IndexError): continue

            elif current_section == SECTION_DEPOSITS:
                try:
                    if any("Gesamt" in col for col in row): continue
                    desc, amount = row[headers["Beschreibung"]], row[headers["Betrag"]]
                    raw_date = row[headers["Abwicklungsdatum"]]

                    dep_id = generate_hash(f"{raw_date}{desc}{amount}")
                    if dep_id in existing_ids: continue

                    date_fmt, _ = parse_date_time(raw_date)
                    new_deposits.append({
                        "id": dep_id, "date": date_fmt, "desc": desc,
                        "amount": to_german_number(amount),
                        "currency": row[headers["Währung"]]
                    })
                    existing_ids.add(dep_id)
                except (KeyError, IndexError): continue
                        
    return new_trades, new_divs, new_deposits, instrument_metadata

def update_xml(new_trades, new_divs, new_deposits, instrument_metadata):
    """Write to XML."""
    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
    except (FileNotFoundError, ET.ParseError):
        root = ET.Element("TradeLog")
        ET.SubElement(root, "Trades")
        ET.SubElement(root, "Dividends")
        ET.SubElement(root, "DepositsWithdrawals")

    trades_node = root.find("Trades")
    for t in new_trades:
        metadata = instrument_metadata.get(t["symbol"], {})
        isin = metadata.get("id", "")
        name = metadata.get("name", "")
        
        if metadata:
            print(f"-> [TC-095] Enriching {t['symbol']} with Name: {name} and ISIN: {isin}")
            
        t_elem = ET.SubElement(trades_node, "Trade", id=t["id"], 
                               name=name, 
                               isin=isin)
        meta = ET.SubElement(t_elem, "Meta")
        ET.SubElement(meta, "Date").text = t["date"]
        ET.SubElement(meta, "Time").text = t["time"]
        instr = ET.SubElement(t_elem, "Instrument")
        ET.SubElement(instr, "Symbol").text = t["symbol"]
        ET.SubElement(instr, "Currency").text = t["currency"]
        ex = ET.SubElement(t_elem, "Execution")
        
        blacklist = ['id', 'date', 'time', 'symbol', 'currency', 'qty', 'price', 'commission', 'proceeds']
        
        for key, val in t.items():
            if key not in blacklist:
                 ET.SubElement(ex, key.capitalize()).text = val

        ET.SubElement(ex, "Quantity").text = t['qty']
        ET.SubElement(ex, "Price").text = t['price']
        ET.SubElement(ex, "Commission").text = t['commission']
        ET.SubElement(ex, "Proceeds").text = t['proceeds']


    divs_node = root.find("Dividends")
    for d in new_divs:
        d_elem = ET.SubElement(divs_node, "Dividend", id=d["id"])
        for key, val in d.items():
            if key != 'id':
                ET.SubElement(d_elem, key.capitalize()).text = val
    
    deps_node = root.find("DepositsWithdrawals")
    if deps_node is None:
        deps_node = ET.SubElement(root, "DepositsWithdrawals")
    for dep in new_deposits:
        dep_elem = ET.SubElement(deps_node, "Transaction", id=dep["id"])
        for key, val in dep.items():
            if key != 'id':
                ET.SubElement(dep_elem, key.capitalize()).text = val

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    xml_str = "\n".join([line for line in xml_str.split("\n") if line.strip()])
    
    with open(XML_FILE, "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    print(f"-> SUCCESS: Saved {len(new_trades)} trades, {len(new_divs)} dividends, {len(new_deposits)} deposits to {XML_FILE}")


def main():
    print("--- IB CSV Converter (Docker v1.0) ---")
    
    ticker_map = {}
    if os.path.exists(TICKER_MAP_FILE):
        try:
            with open(TICKER_MAP_FILE, "r") as f:
                ticker_map = json.load(f)
            print(f"-> [S-IO-220] Loaded {len(ticker_map)} ticker mappings.")
        except json.JSONDecodeError:
            print(f"-> Warning: Could not parse {TICKER_MAP_FILE}.")
    else:
        print(f"-> [TC-080] Ticker map {TICKER_MAP_FILE} not found (optional).")

    csv_path = get_file_path()
    if not csv_path: return

    existing_ids = set()
    if os.path.exists(XML_FILE):
        try:
            tree = ET.parse(XML_FILE)
            existing_ids = load_existing_ids(tree.getroot())
            print(f"-> Loaded {len(existing_ids)} existing entries from {XML_FILE}.")
        except ET.ParseError:
            print(f"-> Warning: {XML_FILE} corrupt. Backing up and starting fresh.")
            try:
                os.rename(XML_FILE, XML_FILE + f".bak_{int(datetime.now().timestamp())}")
            except OSError: pass
    
    new_trades, new_divs, new_deposits, instrument_metadata = process_csv(csv_path, existing_ids, ticker_map)
    
    if new_trades or new_divs or new_deposits:
        update_xml(new_trades, new_divs, new_deposits, instrument_metadata)
    else:
        print("-> No new data found (already imported).")
    
    # Always move processed file to oldcsv directory
    if not os.path.exists(OLD_CSV_DIR):
        os.makedirs(OLD_CSV_DIR)
    
    try:
        new_path = os.path.join(OLD_CSV_DIR, os.path.basename(csv_path))
        os.rename(csv_path, new_path)
        print(f"-> [S-IO-100] Moved processed file to {new_path}")
    except OSError as e:
        print(f"-> Error moving file: {e}")

if __name__ == "__main__":
    main()
