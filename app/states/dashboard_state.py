import reflex as rx
from typing import TypedDict, Literal, cast, Any
import random
from datetime import datetime
import aioboto3
import json
import os
import logging
import asyncio

logger = logging.getLogger(__name__)


class Event(TypedDict):
    timestamp: str
    service: str
    status: Literal["OK", "WARN", "ERROR"]
    message: str
    avatar: str


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

    def _generate_chart_point(self) -> DataPoint:
        last_value = self.chart_data[-1]["value"] if self.chart_data else 150
        change = random.randint(-15, 15)
        new_value = max(20, min(300, last_value + change))
        return {"time": self.time_step, "value": new_value}

    def _create_event_from_sqs(self, message_body: str) -> Event | None:
        try:
            body_json = json.loads(message_body)
            event_source = body_json.get("event_source", "unknown-service")
            payload = body_json.get("payload", {})
            linkedin_id = payload.get("linkedin_identifier", "N/A")
            message = ""
            if "preparation-requested" in event_source:
                source = payload.get("metadata", {}).get("source", "N/A")
                message = f"Prep requested for {linkedin_id} via {source}"
            elif "completed" in event_source:
                job_id = payload.get("job_id", "N/A")
                message = f"Analysis complete for {linkedin_id} (Job: {job_id})"
            elif "events" in event_source:
                job_id = payload.get("job_id", "N/A")
                original_input = payload.get("original_input", "N/A")
                message = f"Event for {original_input} (Job: {job_id})"
            else:
                message = f"Received event from {event_source}"
            timestamp_str = body_json.get(
                "timestamp", datetime.utcnow().isoformat() + "Z"
            )
            dt_object = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return {
                "timestamp": dt_object.strftime("%H:%M:%S"),
                "service": event_source,
                "status": "OK",
                "message": message,
                "avatar": "/icon_gray_simple.png",
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.exception(f"Failed to parse SQS message: {e}")
            return None

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
        session = aioboto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="eu-west-3",
        )
        try:
            async with session.client("sqs") as sqs:
                logger.info("Started SQS long-poll loop")
                while True:
                    async with self:
                        if not self.is_streaming:
                            break
                    try:
                        resp = await sqs.receive_message(
                            QueueUrl=queue_url,
                            MaxNumberOfMessages=10,
                            WaitTimeSeconds=20,
                            MessageAttributeNames=["All"],
                        )
                        messages = resp.get("Messages", [])
                        if not messages:
                            continue
                        delete_entries = []
                        new_events_batch = []
                        new_points_batch = []
                        for m in messages:
                            receipt_handle = m.get("ReceiptHandle")
                            if not receipt_handle:
                                continue
                            new_event = self._create_event_from_sqs(m.get("Body", "{}"))
                            if new_event is None:
                                continue
                            new_events_batch.append(new_event)
                            new_points_batch.append(self._generate_chart_point())
                            delete_entries.append(
                                {"Id": m["MessageId"], "ReceiptHandle": receipt_handle}
                            )
                        if new_events_batch:
                            async with self:
                                self.time_step += len(new_events_batch)
                                self.events = new_events_batch + self.events
                                if len(self.events) > self.MAX_EVENT_LOGS:
                                    self.events = self.events[: self.MAX_EVENT_LOGS]
                                self.chart_data.extend(new_points_batch)
                                if len(self.chart_data) > self.MAX_CHART_POINTS:
                                    self.chart_data = self.chart_data[
                                        -self.MAX_CHART_POINTS :
                                    ]
                                self.stats["total"] += len(new_events_batch)
                                for event in new_events_batch:
                                    st = event["status"]
                                    if st == "OK":
                                        self.stats["ok"] += 1
                                    elif st == "WARN":
                                        self.stats["warn"] += 1
                                    else:
                                        self.stats["error"] += 1
                            yield
                        if delete_entries:
                            await sqs.delete_message_batch(
                                QueueUrl=queue_url, Entries=delete_entries
                            )
                    except asyncio.CancelledError as e:
                        logger.exception("stream_data cancelled; exiting: %s", e)
                        break
                    except Exception as e:
                        logger.exception("SQS loop error: %s", e)
                        await asyncio.sleep(5.0)
        finally:
            logger.info("SQS loop terminated")
            async with self:
                self.is_streaming = False