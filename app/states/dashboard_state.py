import reflex as rx
from typing import TypedDict, Literal
import random
import asyncio
from datetime import datetime
import aioboto3
import json


import logging, sys
logging.basicConfig(
    level=logging.INFO,  # or DEBUG
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # override any defaults
)

logger = logging.getLogger(__name__)

class Event(TypedDict):
    timestamp: str
    service: str
    status: Literal["OK", "WARN", "ERROR"]
    message: str


class DataPoint(TypedDict):
    time: int
    value: int


class DashboardState(rx.State):
    events: list[Event] = []
    chart_data: list[DataPoint] = []
    is_streaming: bool = False
    time_step: int = 0
    stats: dict[str, int] = {"total": 0, "ok": 0, "warn": 0, "error": 0}
    MAX_CHART_POINTS: int = 60
    MAX_EVENT_LOGS: int = 100
    STREAM_INTERVAL_S: float = 1.5
    _services = [
        "Auth Service",
        "API Gateway",
        "Database",
        "Payment Processor",
        "Frontend App",
    ]
    _messages = {
        "OK": [
            "User login successful",
            "API request processed",
            "DB query executed",
            "Payment completed",
            "Page loaded",
        ],
        "WARN": [
            "High latency detected",
            "DB connection pool near capacity",
            "Unusual traffic pattern",
            "API version deprecated",
        ],
        "ERROR": [
            "Authentication failed",
            "Service unavailable (503)",
            "Database connection failed",
            "Payment declined",
            "Critical component crash",
        ],
    }

    def _generate_event(self) -> Event:
        status_choice = random.choices(
            ["OK", "WARN", "ERROR"], weights=[85, 10, 5], k=1
        )[0]
        service = random.choice(self._services)
        message = random.choice(self._messages[status_choice])
        return {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "service": service,
            "status": status_choice,
            "message": f"{message} from {service.split(' ')[0]}",
        }

    def _generate_chart_point(self) -> DataPoint:
        last_value = self.chart_data[-1]["value"] if self.chart_data else 150
        change = random.randint(-15, 15)
        new_value = max(20, min(300, last_value + change))
        return {"time": self.time_step, "value": new_value}

    @rx.event
    def start_streaming_on_load(self):
        self.is_streaming = True
        self.chart_data = []
        self.events = []
        self.stats = {"total": 0, "ok": 0, "warn": 0, "error": 0}
        self.time_step = 0
        return DashboardState.stream_data

    @rx.event(background=True)
    async def stream_data(self):
        queue_url = "https://sqs.eu-west-3.amazonaws.com/183295452065/eggi-dev-reflex-monitoring-events"
        session = aioboto3.Session()
        logger.info("ASDFASDF")

        try:
            async with session.client("sqs", region_name="eu-west-3") as sqs:
                logger.info("Started SQS long-poll loop")
                while self.is_streaming:
                    try:
                        resp = await sqs.receive_message(
                            QueueUrl=queue_url,
                            MaxNumberOfMessages=10,
                            WaitTimeSeconds=20,
                            VisibilityTimeout=60,
                            MessageAttributeNames=["All"],
                            AttributeNames=["SentTimestamp", "ApproximateReceiveCount"],
                        )
                        messages = resp.get("Messages", [])

                        if not messages:
                            logger.info("HELLO")
                            continue

                        # Process batch then delete in batch for efficiency.
                        delete_entries = []
                        for m in messages:
                            logger.info(m)
                            body = m.get("Body", "")
                            try:
                                payload = json.loads(body)
                            except Exception:
                                payload = {"status": "ERROR", "message": body}

                            # Build your domain events / chart point from payload
                            new_event = {
                                "status": payload.get("status", "OK"),
                                "message": payload.get("message", ""),
                                "ts": payload.get("ts"),
                                "meta": payload,
                            }
                            new_point = {
                                "x": payload.get("x", self.time_step + 1),
                                "y": payload.get("y", 1),
                            }

                            async with self:
                                self.time_step += 1
                                self.events.insert(0, new_event)
                                if len(self.events) > self.MAX_EVENT_LOGS:
                                    self.events.pop()

                                self.chart_data.append(new_point)
                                if len(self.chart_data) > self.MAX_CHART_POINTS:
                                    self.chart_data.pop(0)

                                self.stats["total"] += 1
                                st = new_event["status"]
                                if st == "OK":
                                    self.stats["ok"] += 1
                                elif st == "WARN":
                                    self.stats["warn"] += 1
                                else:
                                    self.stats["error"] += 1

                            # push UI update for each message
                            yield

                            delete_entries.append({
                                "Id": m["MessageId"],
                                "ReceiptHandle": m["ReceiptHandle"],
                            })

                        # Best-effort batch delete (avoid redelivery)
                        if delete_entries:
                            await sqs.delete_message_batch(
                                QueueUrl=queue_url,
                                Entries=delete_entries,
                            )

                    except asyncio.CancelledError:
                        logger.info("stream_data cancelled; exiting")
                        break
                    except Exception as e:
                        logger.exception("SQS loop error: %s", e)
                        # brief backoff to avoid hot loop on repeated errors
                        await asyncio.sleep(1.0)

        finally:
            logger.info("SQS loop terminated")