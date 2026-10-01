# Chainlit postMessage Demo

Minimal, didactic example of embedding a Chainlit chat (other domain) inside a host web page and passing the shopper identity through `window.postMessage`. The embedded backend validates the credential server to server before trusting it.

Scenario: a Contoso Store e-commerce site (host page) embeds a GPT-RAG chat UI (embedded page).

| Component | Folder | Azure service | Role |
|---|---|---|---|
| Host page | `host/` | App Service (B1, Linux, Python 3.12) | Fake store with login, issues a short-lived widget token, exposes `GET /api/v1/sessions/current` |
| Embedded page | `embedded/` | Container Apps | Chainlit chat inside an iframe, receives the token and validates it |

Each one has its own public domain, so the browser treats them as different origins.

## Flow

1. **Login on the host.** The user logs in on the host page. The host keeps its own session cookie (HttpOnly, so JavaScript cannot read it).
2. **Iframe loads.** The host page renders an iframe pointing to the Chainlit app.
3. **Embedded says "ready".** Chainlit starts a chat session and calls `cl.send_window_message("ready")` to the parent window.
4. **Host sends the credential.** The host page checks `event.origin` and `event.source`, fetches a short-lived token from its own backend (`GET /api/v1/widget-token`, same origin, cookie is sent automatically) and calls `iframe.contentWindow.postMessage({type: "contoso-auth", token}, EMBEDDED_ORIGIN)`.
5. **Embedded validates server side.** Chainlit receives the message in `@cl.on_window_message` and calls `GET {HOST_URL}/api/v1/sessions/current` with `Authorization: Bearer <token>`. This is a server to server call, so browser CORS does not apply.
6. **User context available.** The response (user name, email, billTo, shipTo) is stored in `cl.user_session` and used to answer questions. The embedded page sends `contoso-auth-ok` back to the host.

References: [Code walkthrough](CODE_WALKTHROUGH.md), [HTML Standard: Web messaging](https://html.spec.whatwg.org/multipage/web-messaging.html#web-messaging), [MDN postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage), [Chainlit window messaging](https://docs.chainlit.io/api-reference/window-message).

## Run locally

```powershell
# terminal 1 - embedded
cd embedded
pip install -r requirements.txt
$env:HOST_URL="http://localhost:5000"
chainlit run app.py --port 8000 --headless

# terminal 2 - host
cd host
pip install -r requirements.txt
$env:EMBEDDED_URL="http://localhost:8000"
$env:SECRET_KEY="dev-secret"
flask --app app run --port 5000
```

Open http://localhost:5000 and log in as `alice` or `bob` (any password).

## Deploy to Azure

```powershell
az group create -n rg-postmessage-demo -l eastus2

# embedded (Container Apps)
cd embedded
az containerapp up -n ca-embedded-chat -g rg-postmessage-demo -l eastus2 `
  --source . --ingress external --target-port 8000 --env-vars HOST_URL=https://placeholder

# host (App Service)
cd ../host
az webapp up -n <host-app-name> -g rg-postmessage-demo -l eastus2 --runtime "PYTHON:3.12" --sku B1
az webapp config appsettings set -n <host-app-name> -g rg-postmessage-demo `
  --settings EMBEDDED_URL=https://<container-app-fqdn> SECRET_KEY=<random>
az webapp config set -n <host-app-name> -g rg-postmessage-demo `
  --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"

# point the embedded app to the host
az containerapp update -n ca-embedded-chat -g rg-postmessage-demo `
  --set-env-vars HOST_URL=https://<host-app-name>.azurewebsites.net
```

Clean up: `az group delete -n rg-postmessage-demo`.

## Production recommendations

This demo is intentionally simplified. For production:

- **Use a dedicated short-lived token.** Issue a signed JWT with `aud`, `iss`, `exp` and `jti` instead of forwarding the store session cookie, and keep it in memory only (never in the URL). See [RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519) and [JWT best practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725).
- **Treat postMessage as transport, not authentication.** Always set an explicit `targetOrigin`, check `event.origin` against an allowlist, and do not send sensitive data back to the parent (Chainlit 2.9.x replies with `"*"`). See [MDN: postMessage security](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage#security_concerns).
- **Validate on the server and fail closed.** The backend calls `GET /api/v1/sessions/current` server-to-server (contract TBC) and derives the user, billTo and shipTo only from that response.
- **Restrict who can frame the chat.** Set CSP [`frame-ancestors`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-ancestors) on the embedded app to the store domains only.
- **Propagate logout and expiry.** When the store session ends, the host notifies the chat, which clears its session.

## Deployed instance (demo)

- Host (App Service, B1, centralus): https://app-host-pm-3955.azurewebsites.net
- Embedded (Container Apps, eastus2): https://ca-embedded-chat.bravewater-65576911.eastus2.azurecontainerapps.io
- Logins: `alice` or `bob` (any password).

Notes:

- The host runs in centralus because the subscription had no B1 quota in eastus2.
- The embedded image was built with `az acr build` and deployed with `az containerapp create/update --image`.
- On Windows, set `$env:PYTHONIOENCODING="utf-8"` before `az acr build` and `az containerapp` commands to avoid encoding errors.
