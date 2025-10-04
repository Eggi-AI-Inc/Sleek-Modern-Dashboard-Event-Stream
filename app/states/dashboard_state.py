import reflex as rx
from typing import TypedDict, Literal
import random
import asyncio
from datetime import datetime


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
        while True:
            async with self:
                if not self.is_streaming:
                    break
                self.time_step += 1
                new_event = self._generate_event()
                new_point = self._generate_chart_point()
                self.events.insert(0, new_event)
                if len(self.events) > self.MAX_EVENT_LOGS:
                    self.events.pop()
                self.chart_data.append(new_point)
                if len(self.chart_data) > self.MAX_CHART_POINTS:
                    self.chart_data.pop(0)
                self.stats["total"] += 1
                if new_event["status"] == "OK":
                    self.stats["ok"] += 1
                elif new_event["status"] == "WARN":
                    self.stats["warn"] += 1
                else:
                    self.stats["error"] += 1
            yield
            await asyncio.sleep(self.STREAM_INTERVAL_S)