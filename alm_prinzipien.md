# ALM Prinzipien - Architektur & Design

Dieses Dokument beschreibt die fundamentalen Prinzipien der Systemarchitektur, die strikt eingehalten werden müssen.

## 1. Verbindungsmanagement (Connection 3.0 - PTA Driven)

### Grundsatz: PTA als Operator
Die technische Verbindung wird **nicht** mehr durch das Start-Skript erzwungen. Stattdessen startet das System "Offline" und der **PTA** übernimmt die Verantwortung für den Verbindungsaufbau.

### Ablauf (PTA Logic)
1.  Systemstart (`run_logger.py`).
2.  PTA führt Auto-Descovery durch:
    *   Versuch 1: Connect `localhost:4002` (Paper Default).
    *   Versuch 2: Connect `localhost:4001` (Live Fallback).
    *   Versuch 3: Nachfrage beim User (Custom IP/Port).
3.  Erfolg/Misserfolg wird im Chat gemeldet.

### Grundsatz: Single Writer (ID 0)
*   **Schreibzugriffe (Orders)** nutzen strikt Client ID `0`.

### Grundsatz: Multi-Reader (Bulk Fetch)
*   Für Massendatenabrufe (`bulk_fetch`) werden temporäre Sessions mit separaten IDs genutzt, um Pacing-Limits zu umgehen.

## 2. Bot-First Principle (Headless & ChatOps)

### Grundsatz: PTA als einziges Frontend
Das System ist für den Betrieb auf **Headless Linux Servern** (ohne GUI) konzipiert. Die primäre Schnittstelle zur Interaktion ist der **Personal Trading Assistant (PTA)** über eine SSH-Verbindung. Es gibt keinen klassischen "Human Mode" mehr; alle Befehle werden natürlichsprachlich an den PTA gerichtet, der diese in strukturierte API-Calls übersetzt.

### Umsetzung
*   **Interaktion**: Ausschließlich via SSH-Terminal.
    *   **Terminal 1 (Control)**: Interaktiver Chat mit dem PTA (`chat`).
    *   **Terminal 2 (Debug)**: Live-Monitoring der Kommunikation (`tail -f logs/communication.log`).
*   **Debug-Modus**: Die Kommunikation zwischen PTA und Backend (Prompt -> JSON-Command -> JSON-Response) muss transparent nachvollziehbar sein.
    *   Das System loggt jeden "Gedankenschritt" und API-Call des PTA in eine separate Log-Datei.
    *   Der User kann via SSH-Co-Session (z.B. `tail -f`) in Echtzeit mitlesen, was der PTA "unter der Haube" tut.
*   **CommandResponse**: Weiterhin strikt strukturiertes JSON für den PTA.
*   **Kein String-Parsing**: Bots parsen niemals Text. Das Frontend (PTA) konsumiert ausschließlich JSON.

## 3. Historische Integrität (Point-in-Time Analysis)

### Grundsatz: Log-basierte Rekonstruktion
Der Zustand des Portfolios zu einem beliebigen Zeitpunkt $T$ wird durch das "Replay" aller Transaktionen und Order-Logs bis zum Zeitpunkt $T$ ermittelt. Single Source of Truth (SSOT) ist das TradeObject.

### Umsetzung
*   **Immutability**: Einmal geschriebene Order-Logs oder Transaktionen werden niemals gelöscht oder nachträglich verändert. Korrekturen erfolgen durch neue, kompensierende Einträge.
*   **Zeitstempel-Filterung**: Jede Analyse-Funktion (`HistoryFactory`, `PortfolioReconstruct`) muss einen `date`-Parameter akzeptieren, um konsistente historische Schnappschüsse zu ermöglichen.
*   **LIFO Konsistenz**: Die Methode der Bestandsbewertung ( LIFO) muss systemweit konsistent in der `PortfolioSnapshot`-Logik angewendet werden.

## 4. Resilienz & Daten-Sicherheit

### Grundsatz: Unabhängigkeit von Live-Daten
Historische Analysen müssen auch dann funktionieren, wenn keine Live-Verbindung zum Broker besteht oder Symbole nicht mehr existieren (Delisted/Dummy-Ticker).

### Umsetzung
*   **Graceful Adapter Failure**: Broker-Adapter dürfen bei fehlschlagender Kontrakt-Qualifizierung (z.B. unbekannter Ticker) oder fehlenden Marktdaten das Gesamtsystem nicht zum Absturz bringen. 
*   **Atomares Speichern**: Speicheroperationen für Trade-Daten (`TradeObject.save()`) erfolgen atomar via Temp-Dateien und `os.rename`, um Datenverlust bei Systemabstürzen zu verhindern.
*   **UUID-Garantie**: Jedes Datenobjekt (`TradeObject`) erhält bei der Erstellung eine unveränderliche, einzigartige ID zur eindeutigen Referenzierung in Logs und Dateisystem.

