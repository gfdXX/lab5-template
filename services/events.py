import json
import os
import time
from functools import lru_cache
from typing import Any, Dict, Optional


@lru_cache()
def _producer():
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap:
        return None
    try:
        from kafka import KafkaProducer

        return KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            retries=1,
            linger_ms=10,
        )
    except Exception as exc:
        print(f"Kafka producer disabled: {exc}")
        return None


def publish_event(
    action: str,
    user: str,
    payload: Dict[str, Any],
    method: Optional[str] = None,
    url: Optional[str] = None,
    status: Optional[int] = None,
) -> None:
    producer = _producer()
    if not producer:
        return
    event = {
        "action": action,
        "user": user,
        "payload": payload,
        "method": method,
        "url": url,
        "status": status,
        "timestamp": int(time.time()),
    }
    try:
        topic = os.getenv("STATS_TOPIC", "car-rental-events")
        producer.send(topic, event)
        producer.flush(timeout=1)
    except Exception as exc:
        print(f"Failed to publish stats event: {exc}")
