# Code walkthrough

Back to [README](README.md). Code links point to commit `81322bc`, so line numbers stay stable.

| Component | Where it runs | Code |
|---|---|---|
| Host page (simulated storefront) | App Service: https://app-host-pm-3955.azurewebsites.net | [host/app.py](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py), [host/templates/index.html](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/templates/index.html) |
| Embedded chat (Chainlit) | Container Apps: https://ca-embedded-chat.bravewater-65576911.eastus2.azurecontainerapps.io | [embedded/app.py](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py) |

## Flow

### 1. Login on the host

The user logs in on the host page. The host keeps its own session cookie (HttpOnly, so JavaScript cannot read it).

- Cookie settings (HttpOnly, SameSite=Lax): [host/app.py L15-L16](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py#L15-L16)
- Fake users (stand in for the commerce customer records): [host/app.py L26-L29](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py#L26-L29)
- Login endpoint, stores the user in the session: [host/app.py L39-L44](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py#L39-L44)
- Login form: [index.html L25-L37](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/templates/index.html#L25-L37)
- More: [MDN: HttpOnly cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#block_access_to_your_cookies)

### 2. Iframe loads

The host page renders an iframe pointing to the Chainlit app.

- Embedded URL and origin derived from config: [host/app.py L18-L20](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py#L18-L20)
- The iframe element: [index.html L47](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/templates/index.html#L47)
- More: [MDN: iframe element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)

### 3. Embedded says "ready"

Chainlit starts a chat session and calls `cl.send_window_message("ready")`, which posts to the parent window.

- `on_chat_start` handler: [embedded/app.py L18-L22](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py#L18-L22)
- More: [Chainlit: Window messaging](https://docs.chainlit.io/api-reference/window-message)

### 4. Host sends the credential

The host page checks `event.origin` and `event.source`, fetches a short-lived token from its own backend (`GET /api/v1/widget-token`, same origin, cookie is sent automatically) and calls `iframe.contentWindow.postMessage({type: "contoso-auth", token}, EMBEDDED_ORIGIN)`.

- Origin and source check: [index.html L55-L59](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/templates/index.html#L55-L59)
- Fetch the widget token (same origin): [index.html L61-L65](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/templates/index.html#L61-L65)
- `postMessage` restricted to the embedded origin: [index.html L67-L69](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/templates/index.html#L67-L69)
- Token endpoint (cookie to signed token, 5 min): [host/app.py L53-L59](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py#L53-L59)
- Token signer and lifetime: [host/app.py L21-L23](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py#L21-L23)
- More: [HTML Standard: Web messaging](https://html.spec.whatwg.org/multipage/web-messaging.html#web-messaging), [MDN: Window.postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)

### 5. Embedded validates server side

Chainlit receives the message in `@cl.on_window_message` and calls `GET {HOST_URL}/api/v1/sessions/current` with `Authorization: Bearer <token>`. This is a server to server call, so browser CORS does not apply.

- Message handler and payload check: [embedded/app.py L25-L30](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py#L25-L30)
- Server to server call to the host: [embedded/app.py L31-L43](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py#L31-L43)
- `HOST_URL` config: [embedded/app.py L15](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py#L15)
- Host side validation of the bearer token: [host/app.py L62-L77](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/app.py#L62-L77)
- More: [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS), [RFC 6750: Bearer token usage](https://datatracker.ietf.org/doc/html/rfc6750)

### 6. User context available

The response (user name, email, billTo, shipTo) is stored in `cl.user_session` and used to answer questions. The embedded page sends `contoso-auth-ok` back to the host.

- Store user in the Chainlit session: [embedded/app.py L45-L52](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py#L45-L52)
- Send `contoso-auth-ok` to the host: [embedded/app.py L53](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py#L53)
- Use the context when answering (simulated RAG): [embedded/app.py L56-L69](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/embedded/app.py#L56-L69)
- Host logs the reply: [index.html L58](https://github.com/placerda/chainlit-postmessage-demo/blob/81322bcc74a53e5faed0f4888cc61e3b3ae6160f/host/templates/index.html#L58)
- More: [Chainlit: User session](https://docs.chainlit.io/concepts/user-session)

## What is simulated in the demo

- `/api/v1/widget-token` and `/api/v1/sessions/current` are mock implementations. The real contract and credential type depend on the commerce platform (TBC).
- Users are hardcoded (alice, bob).
- The RAG answer is a placeholder; a real orchestrator call would pass billTo/shipTo as context.
