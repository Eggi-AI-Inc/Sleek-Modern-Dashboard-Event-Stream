import reflex as rx
from typing import TypedDict, Literal, cast, Optional
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


class QueueAttributes(TypedDict):
    ApproximateNumberOfMessages: str
    ApproximateNumberOfMessagesNotVisible: str
    ApproximateNumberOfMessagesDelayed: str


class DashboardState(rx.State):
    events: list[Event] = []
    is_streaming: bool = False
    stats: dict[str, int] = {"total": 0, "ok": 0, "warn": 0, "error": 0}
    MAX_EVENT_LOGS: int = 100
    QUEUE_NAMES: list[str] = [
        "eggi-mapping-service-profiles-to-analyse",
        "eggi-profiles-to-analyse-preparation",
        "eggi-profile-analysis-completed-supabase-sync",
    ]
    DLQ_QUEUE_NAMES: list[str] = [
        "eggi-mapping-service-profiles-dlq",
        "eggi-profile-analysis-preparation-dlq",
        "eggi-profile-analysis-completed-supabase-sync-dlq",
    ]
    queue_attributes: dict[str, QueueAttributes] = {}

    def _create_event_from_sqs(self, message_body: str) -> Optional[Event]:
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
        self.events = []
        self.stats = {"total": 0, "ok": 0, "warn": 0, "error": 0}
        self.queue_attributes = {
            name: {
                "ApproximateNumberOfMessages": "0",
                "ApproximateNumberOfMessagesNotVisible": "0",
                "ApproximateNumberOfMessagesDelayed": "0",
            }
            for name in self.QUEUE_NAMES + self.DLQ_QUEUE_NAMES
        }
        return [DashboardState.stream_data, DashboardState.update_queue_attributes]

    @rx.event(background=True)
    async def update_queue_attributes(self):
        session = aioboto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="eu-west-3",
        )
        all_queues = self.QUEUE_NAMES + self.DLQ_QUEUE_NAMES
        async with session.client("sqs") as sqs:
            while True:
                async with self:
                    if not self.is_streaming:
                        break
                try:
                    updated_attributes: dict[str, QueueAttributes] = {}
                    for queue_name in all_queues:
                        try:
                            q_url_resp = await sqs.get_queue_url(QueueName=queue_name)
                            q_url = q_url_resp["QueueUrl"]
                            attrs_resp = await sqs.get_queue_attributes(
                                QueueUrl=q_url, AttributeNames=["All"]
                            )
                            attrs = attrs_resp.get("Attributes", {})
                            updated_attributes[queue_name] = {
                                "ApproximateNumberOfMessages": attrs.get(
                                    "ApproximateNumberOfMessages", "N/A"
                                ),
                                "ApproximateNumberOfMessagesNotVisible": attrs.get(
                                    "ApproximateNumberOfMessagesNotVisible", "N/A"
                                ),
                                "ApproximateNumberOfMessagesDelayed": attrs.get(
                                    "ApproximateNumberOfMessagesDelayed", "N/A"
                                ),
                            }
                        except Exception as e:
                            logger.exception(
                                f"Could not fetch attributes for {queue_name}: {e}"
                            )
                            updated_attributes[queue_name] = {
                                "ApproximateNumberOfMessages": "ERR",
                                "ApproximateNumberOfMessagesNotVisible": "ERR",
                                "ApproximateNumberOfMessagesDelayed": "ERR",
                            }
                    async with self:
                        self.queue_attributes = updated_attributes
                except Exception as e:
                    logger.exception("Error in queue attribute update loop: %s", e)
                await asyncio.sleep(1)

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
                        for m in messages:
                            receipt_handle = m.get("ReceiptHandle")
                            if not receipt_handle:
                                continue
                            new_event = self._create_event_from_sqs(m.get("Body", "{}"))
                            if new_event is None:
                                continue
                            new_events_batch.append(new_event)
                            delete_entries.append(
                                {"Id": m["MessageId"], "ReceiptHandle": receipt_handle}
                            )
                        if new_events_batch:
                            async with self:
                                self.events = new_events_batch + self.events
                                if len(self.events) > self.MAX_EVENT_LOGS:
                                    self.events = self.events[: self.MAX_EVENT_LOGS]
                                self.stats["total"] += len(new_events_batch)
                                for event in new_events_batch:
                                    st = event["status"]
                                    if st == "OK":
                                        self.stats["ok"] += 1
                                    elif st == "WARN":
                                        self.stats["warn"] += 1
                                    else:
                                        self.stats["error"] += 1
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