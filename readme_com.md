# Stock-Logger v5 - Kommunikations-Architektur (ChatOps)

Diese Dokumentation beschreibt den Weg einer Nachricht vom Anwender bis zur technischen Ausführung am Broker (IBKR) und zurück. Das System nutzt eine **ChatOps-Architektur**, bei der ein lokales LLM (Large Language Model) als intelligenter Dispatcher agiert.

## Der Nachrichten-Lebenszyklus

Beispiel-Anfrage: `@pta welche aktien hab ich?`

### 1. User Interface (Telnet & Hub)
*   **Eingabe**: Die Kommunikation erfolgt über einen Standard Telnet-Client.
*   **Routing (TelChat Hub)**: Der [TelChat Hub](https://github.com/gnzsnz/telchat) empfängt die Nachricht. Das Präfix `@pta` signalisiert dem Hub, dass die Nachricht an den registrierten Agenten `pta-agent` weitergeleitet werden muss.

### 2. PTA Agent & Bridge (`py_pta`)
*   **Empfang**: Der `pta-agent` ([run_pta.py](file:///app/run_pta.py)) empfängt die Nachricht via TCP.
*   **Bridge ([bridge.py](file:///app/py_pta/bridge.py))**: Die Bridge isoliert den Text und übergibt ihn an den `LLMService`.
*   **KI-Gehirn ([llm_service.py](file:///app/py_pta/llm_service.py))**: Das LLM (z.B. Llama-3 via LM Studio) analysiert die natürliche Sprache.

### 3. Tool-Execution & CLI-Controller
*   **Funktionsaufruf (Tool Call)**: Das LLM erkennt, dass es Daten benötigt. Es ruft das Tool `execute_cli_command` mit dem Argument `command: "status"` auf.
*   **CLI-Controller ([controller.py](file:///app/py_cli/controller.py))**: Die Bridge nimmt diesen Tool-Call entgegen und führt den echten CLI-Befehl im System aus.
*   **Broker-Anbindung ([client.py](file:///app/py_captrader/client.py))**: Der `status`-Befehl nutzt den `IBKRClient` (basierend auf `ib_insync`), um Live-Daten vom **IB-Gateway** abzurufen.

### 4. Antwort-Generierung & Synthese
*   **Daten-Rückfluss**: Das technische Ergebnis (JSON-Liste der Positionen) geht zurück an die Bridge.
*   **Synthese**: Die Bridge füttert das LLM mit diesem Ergebnis. Die KI analysiert die Daten und entscheidet selbstständig über das beste Antwortformat.
*   **Formatierung**: Je nach Modell und Datenlage formuliert die KI entweder eine **natürlichsprachliche Antwort** (z.B. *"Du hast aktuell..."*) oder bereitet die Daten als **Markdown-Tabelle** auf. 
*   **Ausgabe**: Die finale, von der KI generierte Antwort (Text oder Tabelle) wird über den Hub an den Telnet-Client gesendet.

---

## Architektur-Vorteile
*   **Intelligente Aufbereitung**: Da die KI die Antwort generiert, kann sie komplexe Datenmengen automatisch in Tabellen zusammenfassen oder bei Fehlern (z.B. Connection Refused) hilfreiche Tipps geben.
*   **Entkopplung**: Die KI "weiß" nicht, wie man mit Sockets spricht; sie weiß nur, wie man CLI-Befehle bedient.
*   **Sicherheit**: Der `CLIController` validiert alle Befehle, bevor sie ausgeführt werden.
*   **Flexibilität**: Der Anwender kann Fragen stellen, wie er möchte ("was im depot?", "status?", "was hab ich für aktien?"), und die KI wählt immer den passenden technischen Befehl.

## Das "CLI-First" Prinzip

Ein zentrales Merkmal der Architektur ist, dass das System primär als mächtiges Kommandozeilen-Werkzeug (CLI) konzipiert ist. 

### Der PTA als "Virtueller User"
In diesem Setup ist der PTA (die KI) eigentlich nur ein **virtueller Anwender**, der vor derselben Kommandozeile sitzt wie ein menschlicher Operator. 
*   Wenn die KI ein Tool aufruft, "tippt" sie im Hintergrund einen Befehl in den `CLIController`.
*   Das bedeutet: Jeder Befehl, den die KI ausführen kann, steht dir auch direkt in der Shell zur Verfügung (via `python3 main_cli.py [Befehl]`).

### Vorteile dieses Designs
*   **Konsistenz**: Es gibt nur eine einzige Wahrheit für die Geschäftslogik. Ob ein Befehl vom Chatbot oder direkt aus der Konsole kommt – er durchläuft denselben Code.
*   **Transparenz**: Du kannst jederzeit manuell eingreifen oder Befehle testen, die die KI später nutzen soll.
*   **Robustheit**: Die KI "rät" nicht, wie man einen Trade ausführt, sondern nutzt die validierten, technischen Befehle des Systems.

## Netzwerk-Topologie (Docker)
*   **Host-Mode**: Der `pta-agent` läuft im `network_mode: host`, um eine stabile Verbindung zum IB-Gateway (Port 4002) und zum TelChat Hub (Port 9999) über die Loopback-Adresse (`127.0.0.1`) sicherzustellen.
