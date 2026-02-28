"""
Consume Redis stream telegram:outbound; send messages via Telegram API.
Reply context stored in Redis only (reply_context:ctx:{id}, reply_context:chat:{chat_id}).
"""
import base64
import io
import logging
import os

import redis.asyncio as redis

STREAM_KEY = "telegram:outbound"
CONSUMER_GROUP = "telegram-svc"
CONSUMER_NAME = "consumer-1"
REPLY_CTX_PREFIX = "reply_context:ctx:"
REPLY_CHAT_PREFIX = "reply_context:chat:"
REPLY_TTL = 3600  # 1 hour

logger = logging.getLogger(__name__)


async def get_redis() -> redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(url, decode_responses=True)


async def _bot_send_message(application, chat_id: int, text: str):
    await application.bot.send_message(chat_id=chat_id, text=text)


async def _bot_send_document(application, chat_id: int, content: str, filename: str):
    """Send document from string content."""
    bio = io.BytesIO(content.encode("utf-8"))
    bio.name = filename
    await application.bot.send_document(chat_id=chat_id, document=bio, filename=filename)


async def ensure_consumer_group(r: redis.Redis):
    try:
        await r.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info("Created stream group %s", CONSUMER_GROUP)
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            pass
        else:
            raise


async def process_message(application, r: redis.Redis, msg_id: str, data: dict):
    """Process one outbound message and optionally set reply context."""
    msg_type = data.get("type")
    chat_id = data.get("chat_id")
    if chat_id is None:
        logger.warning("Missing chat_id in message %s", msg_id)
        return
    chat_id = int(chat_id)

    reply_context_id = data.get("reply_context_id")
    if reply_context_id:
        # Create reply context in Redis so /token can write back
        ctx_key = f"{REPLY_CTX_PREFIX}{reply_context_id}"
        chat_key = f"{REPLY_CHAT_PREFIX}{chat_id}"
        pipe = r.pipeline()
        pipe.hset(ctx_key, mapping={
            "chat_id": chat_id,
            "status": "pending",
            "reply_text": "",
        })
        pipe.expire(ctx_key, REPLY_TTL)
        pipe.set(chat_key, reply_context_id, ex=REPLY_TTL)
        await pipe.execute()

    if msg_type == "login_url":
        url = data.get("url", "")
        text = (
            "✔ Login initiated. "
            "Please complete login in browser, then send the request token using:\n"
            "/token <request_token>\n\nLogin URL: " + url
        )
        await _bot_send_message(application, chat_id, text)
        logger.info("Sent login URL to %s", chat_id)
    elif msg_type == "text":
        text = data.get("text", "")
        await _bot_send_message(application, chat_id, text)
        logger.info("Sent text to %s", chat_id)
    elif msg_type == "portfolio_report":
        content = data.get("content", "")
        if data.get("base64"):
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
        filename = data.get("filename", "portfolio_report.csv")
        await _bot_send_document(application, chat_id, content, filename)
        logger.info("Sent portfolio report to %s", chat_id)
    else:
        logger.warning("Unknown outbound type: %s", msg_type)


async def consume_outbound_loop(application):
    """Read from telegram:outbound and send messages; ACK after send."""
    r = await get_redis()
    await ensure_consumer_group(r)
    last_id = "0"
    while True:
        try:
            streams = await r.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME, {STREAM_KEY: last_id},
                count=10, block=5000
            )
            if not streams:
                continue
            for stream_name, messages in streams:
                for msg_id, data in messages:
                    try:
                        await process_message(application, r, msg_id, data)
                        await r.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                    except Exception as e:
                        logger.exception("Failed to process %s: %s", msg_id, e)
                    last_id = msg_id
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Stream read error: %s", e)
            await asyncio.sleep(5)


def set_reply_context_token(redis_sync, context_id: str, token: str) -> bool:
    """Set reply text for a context (called when user sends /token XYZ). Returns True if context existed."""
    key = f"{REPLY_CTX_PREFIX}{context_id}"
    if not redis_sync.exists(key):
        return False
    redis_sync.hset(key, mapping={"status": "replied", "reply_text": token})
    redis_sync.expire(key, 300)
    return True


def get_context_id_for_chat(redis_sync, chat_id: int) -> Optional[str]:
    """Get pending reply context_id for this chat (for /token)."""
    key = f"{REPLY_CHAT_PREFIX}{chat_id}"
    return redis_sync.get(key)


def get_reply_from_context(redis_sync, context_id: str) -> Optional[str]:
    """Get reply_text once status is 'replied'. Caller should poll or block."""
    key = f"{REPLY_CTX_PREFIX}{context_id}"
    status = redis_sync.hget(key, "status")
    if status != "replied":
        return None
    return redis_sync.hget(key, "reply_text")
