"""Host page (simulates the Contoso Store e-commerce storefront).

- The shopper logs in; after login the page holds the storefront session token.
- The token is sent to the embedded iframe with postMessage.
- The embedded backend validates the token server-to-server via GET /api/v1/sessions/current.
"""
import os
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config.update(SESSION_COOKIE_SAMESITE="Lax")

EMBEDDED_URL = os.environ.get("EMBEDDED_URL", "http://localhost:8000")
_u = urlparse(EMBEDDED_URL)
EMBEDDED_ORIGIN = f"{_u.scheme}://{_u.netloc}"
TOKEN_MAX_AGE_SECONDS = 8 * 60 * 60

serializer = URLSafeTimedSerializer(app.secret_key, salt="session-token")

# Fake users that stand in for the commerce customer records.
USERS = {
    "alice": {"name": "Alice Smith", "email": "alice@contoso.com", "billTo": "BT-1001", "shipTo": "ST-1001-A"},
    "bob": {"name": "Bob Jones", "email": "bob@fabrikam.com", "billTo": "BT-2002", "shipTo": "ST-2002-B"},
}


@app.get("/")
def index():
    username = session.get("username")
    user = USERS.get(username)
    # The page holds the session token after login, as a SPA does with its bearer token.
    session_token = serializer.dumps({"username": username}) if user else None
    return render_template("index.html", user=user, users=USERS, session_token=session_token,
                           embedded_url=EMBEDDED_URL, embedded_origin=EMBEDDED_ORIGIN)


@app.post("/login")
def login():
    username = request.form.get("username")
    if username in USERS:
        session["username"] = username
    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.get("/api/v1/sessions/current")
def sessions_current():
    """Called server-to-server by the embedded backend with Authorization: Bearer <token>."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify(error="missing bearer token"), 401
    try:
        data = serializer.loads(auth[7:], max_age=TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired:
        return jsonify(error="token expired"), 401
    except BadSignature:
        return jsonify(error="invalid token"), 401
    user = USERS.get(data.get("username"))
    if not user:
        return jsonify(error="unknown user"), 401
    return jsonify(isAuthenticated=True, userName=data["username"], **user)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
