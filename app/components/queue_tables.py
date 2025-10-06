import reflex as rx
from app.states.dashboard_state import DashboardState

QUEUE_DISPLAY_NAMES = {
    "eggi-mapping-service-profiles-to-analyse": "Mapping Service",
    "eggi-profiles-to-analyse-preparation": "Preparation",
    "eggi-profile-analysis-completed-supabase-sync": "Supabase Sync",
    "eggi-mapping-service-profiles-dlq": "Mapping Service DLQ",
    "eggi-profile-analysis-preparation-dlq": "Preparation DLQ",
    "eggi-profile-analysis-completed-supabase-sync-dlq": "Supabase Sync DLQ",
}


def _queue_row(queue_name: str) -> rx.Component:
    attributes = DashboardState.queue_attributes.get(
        queue_name,
        {
            "ApproximateNumberOfMessages": "...",
            "ApproximateNumberOfMessagesNotVisible": "...",
            "ApproximateNumberOfMessagesDelayed": "...",
        },
    )
    return rx.el.tr(
        rx.el.td(
            QUEUE_DISPLAY_NAMES.get(queue_name, queue_name),
            class_name="px-4 py-3 text-sm font-medium text-slate-700",
        ),
        rx.el.td(
            attributes["ApproximateNumberOfMessages"],
            class_name="px-4 py-3 text-sm text-center font-mono text-slate-600",
        ),
        rx.el.td(
            attributes["ApproximateNumberOfMessagesNotVisible"],
            class_name="px-4 py-3 text-sm text-center font-mono text-slate-600",
        ),
        rx.el.td(
            attributes["ApproximateNumberOfMessagesDelayed"],
            class_name="px-4 py-3 text-sm text-center font-mono text-slate-600",
        ),
        class_name="border-b border-slate-100 last:border-b-0",
    )


def _table_header() -> rx.Component:
    return rx.el.thead(
        rx.el.tr(
            rx.el.th(
                "Queue",
                class_name="px-4 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider",
            ),
            rx.el.th(
                rx.el.div(
                    rx.icon("messages-square", size=16),
                    class_name="flex justify-center",
                ),
                class_name="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider",
                title="Approximate Number Of Messages",
            ),
            rx.el.th(
                rx.el.div(
                    rx.icon("loader-circle", size=16), class_name="flex justify-center"
                ),
                class_name="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider",
                title="Approximate Number Of Messages Not Visible",
            ),
            rx.el.th(
                rx.el.div(rx.icon("timer", size=16), class_name="flex justify-center"),
                class_name="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider",
                title="Approximate Number Of Messages Delayed",
            ),
            class_name="bg-slate-50",
        )
    )


def _queue_table(title: str, queue_names: list[str]) -> rx.Component:
    return rx.el.div(
        rx.el.p(title, class_name="font-semibold text-slate-700 text-sm"),
        rx.el.div(
            rx.el.table(
                _table_header(),
                rx.el.tbody(rx.foreach(queue_names, _queue_row), class_name="bg-white"),
                class_name="w-full",
            ),
            class_name="rounded-lg border border-slate-200 overflow-hidden",
        ),
        class_name="flex flex-col gap-3 w-full",
    )


def queue_tables() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                "SQS Queue Depths", class_name="text-lg font-semibold text-slate-800"
            ),
            rx.el.div(
                rx.el.span(class_name="flex size-2 bg-green-500 rounded-full"),
                rx.el.p("Live", class_name="text-sm font-medium text-slate-500"),
                class_name=rx.cond(
                    DashboardState.is_streaming,
                    "flex items-center gap-2 animate-pulse",
                    "flex items-center gap-2 opacity-50",
                ),
            ),
            class_name="flex justify-between items-center",
        ),
        rx.el.div(
            _queue_table("Main Queues", DashboardState.QUEUE_NAMES),
            _queue_table("Dead-Letter Queues", DashboardState.DLQ_QUEUE_NAMES),
            class_name="grid grid-cols-1 gap-6",
        ),
        class_name="p-6 bg-white rounded-2xl border border-slate-200 flex flex-col gap-4",
    )