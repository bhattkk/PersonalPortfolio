"""
Redis: push to telegram:outbound (login URL, portfolio report); reply_context for /token.
Subscribe to telegram:commands for login, watchlist, refresh_sd.
"""
import json
import os
import uuid
import time

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
STREAM_KEY = "telegram:outbound"
COMMANDS_CHAN = "telegram:commands"
REPLY_CTX_PREFIX = "reply_context:ctx:"
REPLY_TTL = 3600
POLL_INTERVAL = 1
POLL_TIMEOUT = 300  # 5 min wait for token


def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def push_login_url(chat_id: int, url: str) -> str:
    """Push login URL to stream with new reply_context_id. Returns context_id."""
    r = get_redis()
    context_id = str(uuid.uuid4())
    payload = {
        "type": "login_url",
        "chat_id": chat_id,
        "reply_context_id": context_id,
        "url": url,
    }
    r.xadd(STREAM_KEY, payload)
    return context_id


def push_text(chat_id: int, text: str):
    get_redis().xadd(STREAM_KEY, {"type": "text", "chat_id": chat_id, "text": text})


def push_portfolio_report(chat_id: int, csv_content: str, filename: str = "portfolio_report.csv"):
    get_redis().xadd(
        STREAM_KEY,
        {
            "type": "portfolio_report",
            "chat_id": chat_id,
            "content": csv_content,
            "filename": filename,
        },
    )


def wait_for_token_reply(context_id: str) -> str | None:
    """Block until reply_context has status=replied; return reply_text or None on timeout."""
    r = get_redis()
    key = f"{REPLY_CTX_PREFIX}{context_id}"
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        status = r.hget(key, "status")
        if status == "replied":
            return r.hget(key, "reply_text")
        time.sleep(POLL_INTERVAL)
    return None


def subscribe_commands(callback):
    """Run pub/sub listener for telegram:commands; callback(cmd_string) for each message."""
    r = get_redis()
    pub = r.pubsub()
    pub.subscribe(COMMANDS_CHAN)
    for message in pub.listen():
        if message["type"] == "message":
            callback(message["data"])
