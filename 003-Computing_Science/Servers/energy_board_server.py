#!/usr/bin/env python3
"""Energy Experts Board — serves on port 8080"""
import http.server, socketserver, os, json, uuid
from datetime import datetime, timezone

PORT = 8080
DIRECTORY = "/home/allenai"
KANBAN_FILE = "/home/allenai/data/kanban_cards.json"


def _load_cards():
    """Load kanban cards from JSON file, returning [] if missing or corrupt."""
    if not os.path.exists(KANBAN_FILE):
        return []
    try:
        with open(KANBAN_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_cards(cards):
    """Persist kanban cards to JSON file."""
    os.makedirs(os.path.dirname(KANBAN_FILE), exist_ok=True)
    with open(KANBAN_FILE, "w") as f:
        json.dump(cards, f, indent=2)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    # ------------------------------------------------------------------ #
    #  CORS headers — included on every response                          #
    # ------------------------------------------------------------------ #
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: int, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        return json.loads(self.rfile.read(length).decode())

    # ------------------------------------------------------------------ #
    #  OPTIONS — pre-flight CORS                                          #
    # ------------------------------------------------------------------ #
    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    # ------------------------------------------------------------------ #
    #  GET                                                                 #
    # ------------------------------------------------------------------ #
    def do_GET(self):
        if self.path == "/api/kanban":
            cards = _load_cards()
            self._send_json(200, cards)
            return
        if self.path == "/" or self.path == "":
            self.path = "/energy_board.html"
        super().do_GET()

    # ------------------------------------------------------------------ #
    #  POST                                                                #
    # ------------------------------------------------------------------ #
    def do_POST(self):
        # POST /api/kanban/add — append a new card
        if self.path == "/api/kanban/add":
            try:
                payload = self._read_json_body()
                if not payload or not isinstance(payload, dict):
                    self._send_json(400, {"error": "JSON object body required"})
                    return

                card = {
                    "id":      str(uuid.uuid4()),
                    "title":   payload.get("title", ""),
                    "notes":   payload.get("notes", ""),
                    "status":  payload.get("column", payload.get("status", "backlog")),
                    "tag":     payload.get("tag", ""),
                    "color":   payload.get("color", ""),
                    "created": datetime.now(timezone.utc).isoformat(),
                }

                cards = _load_cards()
                cards.append(card)
                _save_cards(cards)

                # ── Auto-sync to CRM if this is a New Lead card ──
                if card["status"] in ("backlog", "new_lead", ""):
                    try:
                        import urllib.request as ur
                        import re as _re
                        raw_notes = card.get("notes", "")

                        # Parse each emoji-prefixed line into proper CRM fields
                        def _extract(pattern, text):
                            m = _re.search(pattern, text)
                            return m.group(1).strip() if m else ""

                        phone    = _extract(r'📞\s*([\d\s\(\)\-\+]+)', raw_notes)
                        address  = _extract(r'📍\s*([^\n]+)', raw_notes)
                        city_st  = _extract(r'🏙️\s*([^\n]+)', raw_notes)
                        scope    = _extract(r'📋\s*([^\n]+)', raw_notes)

                        # Combine address + city/state into full address
                        full_address = ', '.join(filter(None, [address, city_st]))

                        # Remaining lines not matched become clean notes
                        clean_notes = scope or ""

                        contact = {
                            "name":    card["title"],
                            "phone":   phone,
                            "address": full_address,
                            "scope":   scope,
                            "notes":   clean_notes,
                            "tag":     card["tag"],
                            "source":  "kanban",
                            "status":  "New Lead",
                            "created": card["created"],
                        }
                        crm_data = json.dumps(contact).encode()
                        crm_req = ur.Request(
                            "http://localhost:8092/api/contacts",
                            data=crm_data,
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        ur.urlopen(crm_req, timeout=3)
                    except Exception as crm_err:
                        pass  # CRM sync failure doesn't block card creation

                self._send_json(201, card)
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # POST /api/kanban/all — replace entire board
        if self.path == "/api/kanban/all":
            try:
                payload = self._read_json_body()
                if not isinstance(payload, list):
                    self._send_json(400, {"error": "JSON array body required"})
                    return

                _save_cards(payload)
                self._send_json(200, {"saved": len(payload)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # Unknown POST path
        self._send_json(404, {"error": "Not found"})

    def log_message(self, fmt, *args): pass


if __name__ == "__main__":
    os.chdir(DIRECTORY)
    # Ensure kanban data file exists on startup
    if not os.path.exists(KANBAN_FILE):
        _save_cards([])
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"✅ Energy Experts Board on port {PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
