# Code walkthrough

Back to [README](README.md). Code links point to commit `3b92651`, so line numbers stay stable.

| Component | Where it runs | Code |
|---|---|---|
| Host page (simulated storefront) | App Service: https://app-host-pm-3955.azurewebsites.net | [host/app.py](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/app.py), [host/templates/index.html](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html) |
| Embedded chat (Chainlit) | Container Apps: https://ca-embedded-chat.bravewater-65576911.eastus2.azurecontainerapps.io | [embedded/app.py](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py) |

## Flow

### 1. Login on the host

The user logs in on the host page. After login, the page holds the session token (in the demo, the host renders it into the page).

- Fake users (stand in for the commerce customer records): [host/app.py L25-L28](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/app.py#L25-L28)
- Login endpoint, stores the user in the session: [host/app.py L41-L46](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/app.py#L41-L46)
- Session token issued for the logged in user: [host/app.py L35-L36](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/app.py#L35-L36)
- Token signer and lifetime: [host/app.py L20-L22](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/app.py#L20-L22)
- Login form: [index.html L26-L36](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html#L26-L36)

### 2. Iframe loads

The host page renders an iframe pointing to the Chainlit app.

- Embedded URL and origin derived from config: [host/app.py L17-L19](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/app.py#L17-L19)
- The iframe element: [index.html L46](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html#L46)
- More: [MDN: iframe element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe)

### 3. Embedded says "ready"

Chainlit starts a chat session and calls `cl.send_window_message("ready")`, which posts to the parent window.

- `on_chat_start` handler: [embedded/app.py L18-L22](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L18-L22)
- More: [Chainlit: Window messaging](https://docs.chainlit.io/api-reference/window-message)

### 4. Host sends the session token

The host page checks `event.origin`, then posts the session token it already holds with `iframe.contentWindow.postMessage({type: "contoso-auth", token}, EMBEDDED_ORIGIN)`. It retries until it receives `contoso-auth-ok`.

- Embedded origin and session token in the page: [index.html L50-L51](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html#L50-L51)
- `postMessage` restricted to the embedded origin: [index.html L58-L63](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html#L58-L63)
- Retries until acknowledged: [index.html L65-L74](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html#L65-L74)
- Origin check, answer to `ready`: [index.html L78-L87](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html#L78-L87)
- More: [HTML Standard: Web messaging](https://html.spec.whatwg.org/multipage/web-messaging.html#web-messaging), [MDN: Window.postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)

### 5. Embedded validates server side

Chainlit receives the message in `@cl.on_window_message` and calls `GET {HOST_URL}/api/v1/sessions/current` with `Authorization: Bearer <token>`. This is a server to server call, so browser CORS does not apply.

- Message handler and payload check: [embedded/app.py L25-L30](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L25-L30)
- Duplicate messages are re-acknowledged: [embedded/app.py L31-L35](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L31-L35)
- Server to server call to the host: [embedded/app.py L36-L48](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L36-L48)
- `HOST_URL` config: [embedded/app.py L15](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L15)
- Host side validation of the bearer token: [host/app.py L55-L70](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/app.py#L55-L70)
- More: [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS), [RFC 6750: Bearer token usage](https://datatracker.ietf.org/doc/html/rfc6750)

### 6. User context available

The response (user name, email, billTo, shipTo) is stored in `cl.user_session` and used to answer questions. The embedded page sends `contoso-auth-ok` back to the host, with no user data in it.

Additional hardening in `embedded/app.py` and `host/templates/index.html`:

- The embedded app returns `Content-Security-Policy: frame-ancestors <host URL>`, so only the host can frame the chat.
- On Logout, the host posts `{type: "contoso-logout"}` to the iframe before submitting; the embedded page clears the user from the Chainlit session.

- Store user in the Chainlit session: [embedded/app.py L50-L57](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L50-L57)
- Send `contoso-auth-ok` to the host: [embedded/app.py L58](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L58)
- Use the context when answering (simulated RAG): [embedded/app.py L61-L74](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/embedded/app.py#L61-L74)
- Host logs the reply: [index.html L88-L92](https://github.com/placerda/chainlit-postmessage-demo/blob/3b92651d4db34a44f99146f6f79ff3194cb1b883/host/templates/index.html#L88-L92)
- More: [Chainlit: User session](https://docs.chainlit.io/concepts/user-session)

## What is simulated in the demo

- `/api/v1/sessions/current` is a mock implementation. The real contract and credential type depend on the commerce platform (TBC).
- Users are hardcoded (alice, bob).
- The RAG answer is a placeholder; a real orchestrator call would pass billTo/shipTo as context.
