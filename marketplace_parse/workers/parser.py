"""Parser worker: consumes ``parse.<slug>`` queue, executes parse_runs.

Run as:
    uv run python -m marketplace_parse.workers.parser --marketplace yandex_market
    uv run python -m marketplace_parse.workers.parser --marketplace wildberries

One worker per marketplace, ``prefetch=1`` so each worker handles exactly one
parse_run at a time. RabbitMQ is the buffer between web and parsing — the queue
holds the burst, the worker processes at its own pace.
"""
import argparse
import asyncio
import json
import logging
from contextlib import suppress

import aio_pika

from marketplace_parse.core.config import settings
from marketplace_parse.mq import queue_name_for
from marketplace_parse.parsers.runner import PARSERS, execute_parse


log = logging.getLogger("marketplace_parse.worker")


async def run_worker(marketplace_slug: str) -> None:
    if marketplace_slug not in PARSERS:
        raise SystemExit(
            f"unknown marketplace slug {marketplace_slug!r}; "
            f"known: {sorted(PARSERS)}"
        )
    qname = queue_name_for(marketplace_slug)
    log.info("connecting to %s, queue %s", settings.rabbitmq_host, qname)
    connection = await aio_pika.connect_robust(settings.rabbitmq_dsn)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(qname, durable=True)
        log.info("waiting for messages on %s (Ctrl-C to stop)", qname)
        async with queue.iterator() as it:
            async for message in it:
                async with message.process(requeue=False, ignore_processed=True):
                    try:
                        payload = json.loads(message.body)
                        run_id = int(payload["run_id"])
                    except (ValueError, KeyError, TypeError) as exc:
                        log.error("bad message body=%r (%s); discarding", message.body, exc)
                        continue
                    log.info("processing run_id=%s", run_id)
                    try:
                        count = await execute_parse(run_id)
                        log.info("run_id=%s done, %d reviews", run_id, count)
                    except Exception as exc:
                        # execute_parse already wrote the failure to parse_runs.error_message.
                        # We swallow it here so the message is ack'd and not redelivered.
                        log.exception("run_id=%s failed: %s", run_id, exc)


def main() -> None:
    p = argparse.ArgumentParser(description="Marketplace parse worker.")
    p.add_argument(
        "--marketplace",
        required=True,
        help=f"marketplace slug; known: {sorted(PARSERS)}",
    )
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    with suppress(KeyboardInterrupt):
        asyncio.run(run_worker(args.marketplace))


if __name__ == "__main__":
    main()
