import reflex as rx
from app.states.dashboard_state import DashboardState, Event


def status_badge(status: rx.Var[str]) -> rx.Component:
    return rx.el.span(
        status,
        class_name=rx.match(
            status,
            (
                "OK",
                "px-2 py-1 text-xs font-semibold text-green-700 bg-green-100 rounded-full",
            ),
            (
                "WARN",
                "px-2 py-1 text-xs font-semibold text-yellow-700 bg-yellow-100 rounded-full",
            ),
            (
                "ERROR",
                "px-2 py-1 text-xs font-semibold text-red-700 bg-red-100 rounded-full",
            ),
            "px-2 py-1 text-xs font-semibold text-slate-700 bg-slate-100 rounded-full",
        ),
    )


def event_row(event: Event) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            status_badge(event["status"]),
            rx.el.span(event["timestamp"], class_name="text-xs text-slate-500"),
            class_name="flex items-center justify-between",
        ),
        rx.el.p(event["service"], class_name="font-medium text-slate-700"),
        rx.el.p(event["message"], class_name="text-sm text-slate-500"),
        class_name="flex flex-col gap-1 p-4 border-b border-slate-100",
    )


def event_stream() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                "Live Event Stream", class_name="text-lg font-semibold text-slate-800"
            ),
            rx.el.div(
                rx.el.span(class_name="flex size-2 bg-green-500 rounded-full"),
                rx.el.p("Live", class_name="text-sm font-medium text-slate-500"),
                class_name="flex items-center gap-2 animate-pulse",
            ),
            class_name="flex justify-between items-center p-6 border-b border-slate-200",
        ),
        rx.el.div(
            rx.foreach(DashboardState.events, event_row),
            class_name="overflow-y-auto h-full",
        ),
        class_name="bg-white rounded-2xl border border-slate-200 flex flex-col w-full lg:w-1/3",
    )