import asyncio
import json

import aio_pika

from marketplace_parse.core.config import settings


def queue_name_for(marketplace_slug: str) -> str:
    return f"parse.{marketplace_slug}"


_connection: aio_pika.abc.AbstractRobustConnection | None = None
_publish_channel: aio_pika.abc.AbstractChannel | None = None
_lock = asyncio.Lock()


async def _get_publish_channel() -> aio_pika.abc.AbstractChannel:
    global _connection, _publish_channel
    async with _lock:
        if _connection is None or _connection.is_closed:
            _connection = await aio_pika.connect_robust(settings.rabbitmq_dsn)
        if _publish_channel is None or _publish_channel.is_closed:
            _publish_channel = await _connection.channel()
        return _publish_channel


async def publish_parse_task(run_id: int, marketplace_slug: str) -> None:
    channel = await _get_publish_channel()
    qname = queue_name_for(marketplace_slug)
    await channel.declare_queue(qname, durable=True)
    body = json.dumps({"run_id": run_id}).encode()
    await channel.default_exchange.publish(
        aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=qname,
    )


async def disconnect() -> None:
    global _connection, _publish_channel
    if _publish_channel is not None and not _publish_channel.is_closed:
        await _publish_channel.close()
    _publish_channel = None
    if _connection is not None and not _connection.is_closed:
        await _connection.close()
    _connection = None
