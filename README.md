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

## What this demo simplifies (production items)

The host main page has a collapsible **Production recommendations** section with the full list (credential design, postMessage hardening, server-side validation, iframe session, framing policy, platform and operations). Summary:

- **postMessage is a transport, not authentication.** Anything can post a message to the iframe. Trust comes only from validating the token on the server.
- **Origin checks.** The host checks `event.origin`. Chainlit 2.9.x forwards any window message without an origin check and replies with target `"*"`, so do not send sensitive data back to the parent.
- **Real contract TBC.** The real `GET /api/v1/sessions/current` contract on the commerce platform (which credential it accepts, which fields it returns, billTo/shipTo shape) still needs confirmation.
- **Token design.** Prefer a short-lived, audience-bound token instead of reusing the store session cookie. An HttpOnly cookie cannot be read by JavaScript, so it cannot be forwarded through postMessage.
- **Chainlit auth.** Here the identity lives only in `cl.user_session`. In production, consider Chainlit header or custom auth so threads and history are tied to the user.
- **Third-party cookies.** Inside an iframe the Chainlit cookies are third-party and may be blocked by some browsers. Test Safari and Chrome with restrictions.
- **Framing policy.** Use CSP `frame-ancestors` on the embedded app to allow only the store domain.
- **Logout and session expiry.** Propagate logout and token expiry from the host to the embedded chat.

## Deployed instance (demo)

- Host (App Service, B1, centralus): https://app-host-pm-3955.azurewebsites.net
- Embedded (Container Apps, eastus2): https://ca-embedded-chat.bravewater-65576911.eastus2.azurecontainerapps.io
- Logins: `alice` or `bob` (any password).

Notes:

- The host runs in centralus because the subscription had no B1 quota in eastus2.
- The embedded image was built with `az acr build` and deployed with `az containerapp create/update --image`.
- On Windows, set `$env:PYTHONIOENCODING="utf-8"` before `az acr build` and `az containerapp` commands to avoid encoding errors.
