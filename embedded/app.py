"""Embedded chat (simulates the GPT-RAG Chainlit UI running in Container Apps).

Flow:
1. on_chat_start sends "ready" to the parent window (window.parent.postMessage).
2. The host page answers with {"type": "contoso-auth", "token": "..."}.
3. on_window_message receives it and validates the token server-to-server
   by calling HOST_URL/api/v1/sessions/current.
4. The validated user context (bill-to, ship-to) is stored in the Chainlit user session.
"""
import os
from urllib.parse import urlparse

import chainlit as cl
import httpx
from chainlit.server import app as fastapi_app

HOST_URL = os.environ.get("HOST_URL", "http://localhost:5000").rstrip("/")
_host = urlparse(HOST_URL)
ALLOWED_PARENT_ORIGIN = os.environ.get("ALLOWED_PARENT_ORIGIN", f"{_host.scheme}://{_host.netloc}")


@fastapi_app.middleware("http")
async def frame_ancestors(request, call_next):
    # Only the host page origin may embed this app in an iframe.
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = f"frame-ancestors {ALLOWED_PARENT_ORIGIN}"
    return response


@cl.on_chat_start
async def start():
    cl.user_session.set("user", None)
    await cl.Message(content="Waiting for the host page to send the shopper credential...").send()
    await cl.send_window_message("ready")


@cl.on_window_message
async def window_message(data):
    # Chainlit does not check the sender origin, so never trust the payload itself:
    # the token is only accepted after the host backend validates it.
    if not isinstance(data, dict):
        return
    if data.get("type") == "contoso-logout":
        # The host signed the shopper out: drop the identity from this chat session.
        if cl.user_session.get("user"):
            cl.user_session.set("user", None)
            await cl.Message(content="Session ended on the host page. Sign in again to continue.").send()
        return
    if data.get("type") != "contoso-auth" or not data.get("token"):
        return
    # The host retries until it gets an ack, so duplicates are expected: just re-ack.
    current = cl.user_session.get("user")
    if current:
        await cl.send_window_message({"type": "contoso-auth-ok"})
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{HOST_URL}/api/v1/sessions/current",
                headers={"Authorization": f"Bearer {data['token']}"},
            )
    except httpx.HTTPError as exc:
        await cl.Message(content=f"Could not reach the host backend: {exc}").send()
        return

    if resp.status_code != 200:
        await cl.Message(content=f"Authentication failed ({resp.status_code}): {resp.text}").send()
        return

    user = resp.json()
    cl.user_session.set("user", user)
    await cl.Message(
        content=(
            f"Authenticated as **{user['name']}** ({user['email']})\n\n"
            f"Bill-to: `{user['billTo']}` | Ship-to: `{user['shipTo']}`"
        )
    ).send()
    await cl.send_window_message({"type": "contoso-auth-ok"})


@cl.on_message
async def on_message(message: cl.Message):
    user = cl.user_session.get("user")
    if not user:
        await cl.Message(content="Not authenticated yet. Open this chat from the host page.").send()
        return
    # Simulated RAG answer. A real orchestrator call would pass billTo/shipTo as context.
    await cl.Message(
        content=(
            f"(simulated answer) You asked: '{message.content}'.\n\n"
            f"I would search products and prices for bill-to `{user['billTo']}` "
            f"and ship-to `{user['shipTo']}`."
        )
    ).send()
