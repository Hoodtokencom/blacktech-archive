#!/usr/bin/env python3
"""
PIN Login Module for Blacktech Dashboards
Simple 4-digit PIN auth with session cookies.

Usage in any Flask app:
    from pin_auth import require_pin, init_pin_auth
    init_pin_auth(app, pin="7319")
    @app.route("/admin")
    @require_pin
    def admin():
        return "Secret data"
"""

from flask import Flask, request, redirect, render_template_string, make_response, session
import functools
import os
import time

# ── CONFIG ─────────────────────────────────────────
DEFAULT_PIN = "7319"
SESSION_COOKIE = "blacktech_pin"
SESSION_DURATION = 8 * 3600  # 8 hours
FAILED_ATTEMPTS = {}
MAX_FAILS = 5
LOCKOUT_SECONDS = 300  # 5 min

# ── HTML ───────────────────────────────────────────
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🔐 Blacktech Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0f;
            color: #fff;
            font-family: 'Segoe UI', Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            text-align: center;
            width: 100%;
            max-width: 360px;
            padding: 20px;
        }
        .logo {
            font-size: 48px;
            margin-bottom: 10px;
        }
        h1 {
            font-size: 20px;
            color: #00b4d8;
            margin-bottom: 30px;
            font-weight: 300;
        }
        .pin-display {
            background: #111118;
            border: 2px solid #00b4d8;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            font-size: 36px;
            letter-spacing: 12px;
            min-height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .pin-dots {
            display: flex;
            gap: 12px;
            justify-content: center;
        }
        .dot {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #333;
            transition: all 0.2s;
        }
        .dot.filled {
            background: #00b4d8;
            box-shadow: 0 0 10px #00b4d8;
        }
        .keypad {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        .key {
            background: #1a1a24;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 20px;
            font-size: 24px;
            color: #fff;
            cursor: pointer;
            transition: all 0.15s;
            user-select: none;
        }
        .key:hover {
            background: #00b4d8;
            border-color: #00b4d8;
        }
        .key:active {
            transform: scale(0.95);
        }
        .key.action {
            background: #ff3355;
            border-color: #ff3355;
        }
        .key.action:hover {
            background: #ff5577;
        }
        .error {
            color: #ff3355;
            font-size: 14px;
            margin-bottom: 15px;
            min-height: 20px;
        }
        .hint {
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🛡️</div>
        <h1>Blacktech Command Center</h1>
        <div class="pin-display">
            <div class="pin-dots" id="dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        </div>
        <div class="error" id="error">{{ error }}</div>
        <div class="keypad">
            <div class="key" onclick="press('1')">1</div>
            <div class="key" onclick="press('2')">2</div>
            <div class="key" onclick="press('3')">3</div>
            <div class="key" onclick="press('4')">4</div>
            <div class="key" onclick="press('5')">5</div>
            <div class="key" onclick="press('6')">6</div>
            <div class="key" onclick="press('7')">7</div>
            <div class="key" onclick="press('8')">8</div>
            <div class="key" onclick="press('9')">9</div>
            <div class="key" onclick="press('0')">0</div>
            <div class="key action" onclick="clearPin()">⌫</div>
            <div class="key action" onclick="submitPin()">→</div>
        </div>
        <div class="hint">Enter 4-digit PIN to access</div>
    </div>
    <form method="POST" action="/pin-login" id="form" style="display:none">
        <input type="hidden" name="pin" id="pinInput">
        <input type="hidden" name="next" id="nextInput" value="{{ next_url }}">
    </form>
    <script>
        let pin = "";
        function press(d) {
            if (pin.length < 4) {
                pin += d;
                updateDots();
            }
            if (pin.length === 4) {
                setTimeout(submitPin, 200);
            }
        }
        function clearPin() {
            pin = "";
            updateDots();
            document.getElementById("error").textContent = "";
        }
        function updateDots() {
            const dots = document.querySelectorAll(".dot");
            dots.forEach((d, i) => {
                d.classList.toggle("filled", i < pin.length);
            });
        }
        function submitPin() {
            if (pin.length === 4) {
                document.getElementById("pinInput").value = pin;
                document.getElementById("form").submit();
            }
        }
        document.addEventListener("keydown", function(e) {
            if (e.key >= "0" && e.key <= "9") press(e.key);
            if (e.key === "Backspace") clearPin();
            if (e.key === "Enter") submitPin();
        });
    </script>
</body>
</html>
"""

# ── CORE FUNCTIONS ─────────────────────────────────

def check_pin(pin_code, app_pin):
    """Validate PIN with brute-force protection."""
    client_ip = request.remote_addr or "unknown"
    now = time.time()

    # Check lockout
    if client_ip in FAILED_ATTEMPTS:
        fails, last = FAILED_ATTEMPTS[client_ip]
        if fails >= MAX_FAILS and (now - last) < LOCKOUT_SECONDS:
            remaining = int(LOCKOUT_SECONDS - (now - last))
            return False, f"Locked out. Try again in {remaining} seconds."
        elif (now - last) > LOCKOUT_SECONDS:
            FAILED_ATTEMPTS[client_ip] = (0, now)

    if pin_code == app_pin:
        FAILED_ATTEMPTS[client_ip] = (0, now)
        return True, None

    # Track failure
    fails, _ = FAILED_ATTEMPTS.get(client_ip, (0, now))
    FAILED_ATTEMPTS[client_ip] = (fails + 1, now)
    remaining = MAX_FAILS - fails - 1
    return False, f"Wrong PIN. {remaining} attempts remaining."


def is_authenticated():
    """Check if session cookie is valid."""
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return False
    try:
        parts = cookie.split(":")
        if len(parts) != 2:
            return False
        timestamp = int(parts[1])
        if time.time() - timestamp > SESSION_DURATION:
            return False
        return True
    except Exception:
        return False


def require_pin(f):
    """Decorator: require PIN before accessing route."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if is_authenticated():
            return f(*args, **kwargs)
        return redirect(f"/pin-login?next={request.path}")
    return decorated


# ── FLASK INTEGRATION ──────────────────────────────

def init_pin_auth(app, pin=DEFAULT_PIN, secret_key=None):
    """
    Add PIN login to a Flask app.

    Args:
        app: Flask app instance
        pin: 4-digit PIN string (default: 7319)
        secret_key: Optional secret for session signing
    """
    if secret_key:
        app.secret_key = secret_key
    elif not app.secret_key:
        app.secret_key = os.urandom(24)

    # Login page
    @app.route("/pin-login", methods=["GET", "POST"])
    def pin_login():
        error = ""
        next_url = request.args.get("next", "/")

        if request.method == "POST":
            entered = request.form.get("pin", "").strip()
            next_url = request.form.get("next", "/")
            ok, msg = check_pin(entered, pin)
            if ok:
                resp = make_response(redirect(next_url))
                timestamp = str(int(time.time()))
                resp.set_cookie(SESSION_COOKIE, f"ok:{timestamp}", max_age=SESSION_DURATION, httponly=True, samesite="Lax")
                return resp
            else:
                error = msg

        return render_template_string(LOGIN_HTML, error=error, next_url=next_url)

    # Logout
    @app.route("/pin-logout")
    def pin_logout():
        resp = make_response(redirect("/pin-login"))
        resp.set_cookie(SESSION_COOKIE, "", expires=0)
        return resp

    print(f"[PIN-AUTH] 🔐 PIN login enabled. PIN: {pin}")
    print(f"[PIN-AUTH] Login at: /pin-login")
    print(f"[PIN-AUTH] Logout at: /pin-logout")


# ── STANDALONE LOGIN GATEWAY ───────────────────────

def create_pin_gateway(pin=DEFAULT_PIN, target_url="http://127.0.0.1:8090", port=8099):
    """
    Create a standalone Flask app that proxies to another service
    after PIN authentication. Useful for wrapping non-Flask apps.
    """
    from werkzeug.middleware.proxy_fix import ProxyFix

    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    init_pin_auth(app, pin=pin)

    import requests

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    @require_pin
    def proxy(path):
        target = f"{target_url}/{path}"
        try:
            resp = requests.request(
                method=request.method,
                url=target,
                headers={k: v for k, v in request.headers if k.lower() != "host"},
                data=request.get_data(),
                cookies=request.cookies,
                timeout=30
            )
            return (resp.content, resp.status_code, resp.headers.items())
        except Exception as e:
            return f"Gateway error: {e}", 502

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    return app


# ── MAIN (demo) ────────────────────────────────────
if __name__ == "__main__":
    # Demo: run standalone protected dashboard
    app = Flask(__name__)
    app.secret_key = "demo-secret-key-123"
    init_pin_auth(app, pin=DEFAULT_PIN)

    @app.route("/")
    @require_pin
    def home():
        return """
        <!DOCTYPE html>
        <html><head><style>
            body { background: #0a0a0f; color: #fff; font-family: sans-serif; padding: 40px; }
            h1 { color: #00b4d8; }
            a { color: #ff3355; }
        </style></head><body>
            <h1>✅ PIN Authentication Active</h1>
            <p>You are logged in.</p>
            <p><a href="/pin-logout">🔒 Logout</a></p>
        </body></html>
        """

    print(f"\n{'='*50}")
    print("🔐  PIN LOGIN DEMO RUNNING")
    print(f"{'='*50}")
    print(f"URL: http://127.0.0.1:8099")
    print(f"PIN: {DEFAULT_PIN}")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=8099, debug=False)
