import asyncio
import json
from typing import Any

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
except Exception:  # pragma: no cover - optional dependency
    AIOKafkaConsumer = None
    AIOKafkaProducer = None

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.telemetry import NetworkFlowIn
from app.services.defense_orchestrator import DefenseOrchestrator


class KafkaTelemetryStream:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._producer: AIOKafkaProducer | None = None
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None
        self._running = False

    @property
    def enabled(self) -> bool:
        return bool(self.settings.kafka_enabled and AIOKafkaProducer and AIOKafkaConsumer)

    async def start(self) -> None:
        if not self.enabled or self._running:
            return
        self._producer = AIOKafkaProducer(bootstrap_servers=self.settings.kafka_bootstrap_servers)
        self._consumer = AIOKafkaConsumer(
            self.settings.kafka_network_topic,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=self.settings.kafka_consumer_group,
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        try:
            await self._producer.start()
            await self._consumer.start()
            self._running = True
            self._task = asyncio.create_task(self._consume_loop())
        except Exception:
            self._running = False
            if self._consumer:
                await self._consumer.stop()
            if self._producer:
                await self._producer.stop()
            self._consumer = None
            self._producer = None

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        self._task = None
        self._consumer = None
        self._producer = None

    async def publish_network_flow(self, payload: dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        if not self._producer:
            await self.start()
        if not self._producer:
            return False
        await self._producer.send_and_wait(
            self.settings.kafka_network_topic,
            json.dumps(payload).encode("utf-8"),
        )
        return True

    async def _consume_loop(self) -> None:
        if not self._consumer:
            return
        while self._running:
            try:
                message = await self._consumer.getone()
                data = json.loads(message.value.decode("utf-8"))
                payload = NetworkFlowIn(**data)
                with SessionLocal() as db:
                    DefenseOrchestrator(db).evaluate_network_flow(payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(0.5)


kafka_stream = KafkaTelemetryStream()
