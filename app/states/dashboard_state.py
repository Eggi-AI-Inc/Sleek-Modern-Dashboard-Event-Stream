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
    # Environment toggle: False -> prod, True -> dev
    use_dev_queues: bool = False

    # Base (prod) queue names; dev variant will replace "eggi-" with "eggi-dev-"
    # Order: preparation -> mapping -> completion -> llm
    QUEUE_BASE_NAMES: list[str] = [
        "eggi-profiles-to-analyse-preparation",
        "eggi-mapping-service-profiles-to-analyse",
        "eggi-mapping-job-completion-handler",
        "eggi-llm-inference-jobs",
    ]
    DLQ_BASE_NAMES: list[str] = [
        "eggi-profile-analysis-preparation-dlq",
        "eggi-mapping-service-profiles-dlq",
        "eggi-mapping-job-completion-handler-dlq",
        "eggi-llm-inference-jobs-dlq",
    ]
    queue_attributes: dict[str, QueueAttributes] = {}

    @rx.var
    def queue_names(self) -> list[str]:
        if self.use_dev_queues:
            return [name.replace("eggi-", "eggi-dev-") for name in self.QUEUE_BASE_NAMES]
        return list(self.QUEUE_BASE_NAMES)

    @rx.var
    def dlq_queue_names(self) -> list[str]:
        if self.use_dev_queues:
            return [name.replace("eggi-", "eggi-dev-") for name in self.DLQ_BASE_NAMES]
        return list(self.DLQ_BASE_NAMES)

    @rx.event
    def set_use_dev_queues(self, value: bool):
        self.use_dev_queues = bool(value)
        if self.is_streaming:
            # Stop current background tasks and restart with the new queue set
            self.is_streaming = False
            return [DashboardState.start_streaming_on_load]

    @rx.var
    def queues_with_attrs(self) -> list[tuple[str, QueueAttributes]]:
        result: list[tuple[str, QueueAttributes]] = []
        existing = self.queue_attributes or {}
        for name in self.queue_names:
            attrs = existing.get(name)
            if attrs is None:
                counterpart = (
                    name.replace("eggi-dev-", "eggi-")
                    if name.startswith("eggi-dev-")
                    else name.replace("eggi-", "eggi-dev-")
                )
                attrs = existing.get(counterpart) or {
                    "ApproximateNumberOfMessages": "0",
                    "ApproximateNumberOfMessagesNotVisible": "0",
                    "ApproximateNumberOfMessagesDelayed": "0",
                }
            result.append((name, attrs))
        return result

    @rx.var
    def dlq_queues_with_attrs(self) -> list[tuple[str, QueueAttributes]]:
        result: list[tuple[str, QueueAttributes]] = []
        existing = self.queue_attributes or {}
        for name in self.dlq_queue_names:
            attrs = existing.get(name)
            if attrs is None:
                counterpart = (
                    name.replace("eggi-dev-", "eggi-")
                    if name.startswith("eggi-dev-")
                    else name.replace("eggi-", "eggi-dev-")
                )
                attrs = existing.get(counterpart) or {
                    "ApproximateNumberOfMessages": "0",
                    "ApproximateNumberOfMessagesNotVisible": "0",
                    "ApproximateNumberOfMessagesDelayed": "0",
                }
            result.append((name, attrs))
        return result

    @rx.var
    def queue_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for name, attrs in self.queues_with_attrs:
            rows.append(
                {
                    "name": name,
                    "ApproximateNumberOfMessages": attrs["ApproximateNumberOfMessages"],
                    "ApproximateNumberOfMessagesNotVisible": attrs[
                        "ApproximateNumberOfMessagesNotVisible"
                    ],
                    "ApproximateNumberOfMessagesDelayed": attrs[
                        "ApproximateNumberOfMessagesDelayed"
                    ],
                }
            )
        return rows

    @rx.var
    def dlq_queue_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for name, attrs in self.dlq_queues_with_attrs:
            rows.append(
                {
                    "name": name,
                    "ApproximateNumberOfMessages": attrs["ApproximateNumberOfMessages"],
                    "ApproximateNumberOfMessagesNotVisible": attrs[
                        "ApproximateNumberOfMessagesNotVisible"
                    ],
                    "ApproximateNumberOfMessagesDelayed": attrs[
                        "ApproximateNumberOfMessagesDelayed"
                    ],
                }
            )
        return rows

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
        # Preserve existing attributes and seed missing queues from their base/dev counterpart
        # to avoid UI resets when toggling environments.
        existing = self.queue_attributes or {}
        target_names = self.queue_names + self.dlq_queue_names
        new_attrs: dict[str, QueueAttributes] = dict(existing)
        for name in target_names:
            if name in new_attrs:
                continue
            # Try to seed from the opposite env name if present
            if name.startswith("eggi-dev-"):
                counterpart = name.replace("eggi-dev-", "eggi-")
            else:
                counterpart = name.replace("eggi-", "eggi-dev-")
            seed = existing.get(counterpart)
            if seed is None:
                seed = {
                    "ApproximateNumberOfMessages": existing.get(name, {}).get(
                        "ApproximateNumberOfMessages", "0"
                    ),
                    "ApproximateNumberOfMessagesNotVisible": existing.get(name, {}).get(
                        "ApproximateNumberOfMessagesNotVisible", "0"
                    ),
                    "ApproximateNumberOfMessagesDelayed": existing.get(name, {}).get(
                        "ApproximateNumberOfMessagesDelayed", "0"
                    ),
                }
            new_attrs[name] = seed  # type: ignore[assignment]
        self.queue_attributes = new_attrs
        return [DashboardState.stream_data, DashboardState.update_queue_attributes]

    @rx.event(background=True)
    async def update_queue_attributes(self):
        session = aioboto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name="eu-west-3",
        )
        all_queues = self.queue_names + self.dlq_queue_names
        async with session.client("sqs") as sqs:
            while True:
                async with self:
                    if not self.is_streaming:
                        break
                try:
                    # Start from the previous values to avoid flashing placeholders.
                    prev_attributes: dict[str, QueueAttributes] = self.queue_attributes or {}
                    updated_attributes: dict[str, QueueAttributes] = dict(prev_attributes)
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
                                    "ApproximateNumberOfMessages",
                                    prev_attributes.get(queue_name, {}).get(
                                        "ApproximateNumberOfMessages", "0"
                                    ),
                                ),
                                "ApproximateNumberOfMessagesNotVisible": attrs.get(
                                    "ApproximateNumberOfMessagesNotVisible",
                                    prev_attributes.get(queue_name, {}).get(
                                        "ApproximateNumberOfMessagesNotVisible", "0"
                                    ),
                                ),
                                "ApproximateNumberOfMessagesDelayed": attrs.get(
                                    "ApproximateNumberOfMessagesDelayed",
                                    prev_attributes.get(queue_name, {}).get(
                                        "ApproximateNumberOfMessagesDelayed", "0"
                                    ),
                                ),
                            }
                        except Exception as e:
                            # Preserve previous values on error to avoid UI flicker.
                            logger.exception(
                                f"Could not fetch attributes for {queue_name}: {e}"
                            )
                            if queue_name not in updated_attributes:
                                updated_attributes[queue_name] = prev_attributes.get(
                                    queue_name,
                                    {
                                        "ApproximateNumberOfMessages": "0",
                                        "ApproximateNumberOfMessagesNotVisible": "0",
                                        "ApproximateNumberOfMessagesDelayed": "0",
                                    },
                                )
                    async with self:
                        self.queue_attributes = updated_attributes
                except Exception as e:
                    logger.exception("Error in queue attribute update loop: %s", e)
                await asyncio.sleep(1)

    @rx.event(background=True)
    async def stream_data(self):
        base_queue = "eggi-llm-inference-jobs"
        selected_queue = (
            base_queue.replace("eggi-", "eggi-dev-") if self.use_dev_queues else base_queue
        )
        queue_url = f"https://sqs.eu-west-3.amazonaws.com/183295452065/{selected_queue}"
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