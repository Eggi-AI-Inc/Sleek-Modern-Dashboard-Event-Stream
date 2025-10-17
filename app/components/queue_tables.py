import reflex as rx
from app.states.dashboard_state import DashboardState

QUEUE_DISPLAY_NAMES = {
    "eggi-profiles-to-analyse-preparation": "Preparation",
    "eggi-mapping-service-profiles-to-analyse": "Mapping Service",
    "eggi-mapping-job-completion-handler": "Completion Handler",
    "eggi-llm-inference-jobs": "LLM Inference Jobs",
    "eggi-profile-analysis-preparation-dlq": "Preparation DLQ",
    "eggi-mapping-service-profiles-dlq": "Mapping Service DLQ",
    "eggi-mapping-job-completion-handler-dlq": "Completion Handler DLQ",
    "eggi-llm-inference-jobs-dlq": "LLM Inference Jobs DLQ",
}


def _queue_row(row: dict[str, str]) -> rx.Component:
    queue_name = row["name"]
    return rx.el.tr(
        rx.el.td(
            QUEUE_DISPLAY_NAMES.get(queue_name.replace("eggi-dev-", "eggi-"), queue_name),
            class_name="px-4 py-3 text-sm font-medium text-slate-700 truncate whitespace-nowrap",
            style={"width": "200px"},
        ),
        rx.el.td(
            row["ApproximateNumberOfMessages"],
            class_name="px-4 py-3 text-sm text-center font-mono text-slate-600 min-w-0 overflow-hidden",
            style={"width": "1.25rem", "maxWidth": "1.25rem"},
        ),
        rx.el.td(
            row["ApproximateNumberOfMessagesNotVisible"],
            class_name="px-4 py-3 text-sm text-center font-mono text-slate-600 min-w-0 overflow-hidden",
            style={"width": "1.25rem", "maxWidth": "1.25rem"},
        ),
        rx.el.td(
            row["ApproximateNumberOfMessagesDelayed"],
            class_name="px-4 py-3 text-sm text-center font-mono text-slate-600 min-w-0 overflow-hidden",
            style={"width": "1.25rem", "maxWidth": "1.25rem"},
        ),
        class_name="border-b border-slate-100 last:border-b-0",
    )


def _table_header() -> rx.Component:
    return rx.el.thead(
        rx.el.tr(
            rx.el.th(
                "Queue",
                class_name="px-4 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider",
                style={"width": "200px"},
            ),
            rx.el.th(
                rx.el.div(
                    rx.icon("messages-square", size=16),
                    class_name="flex justify-center",
                ),
                class_name="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-0",
                style={"width": "1.25rem", "maxWidth": "1.25rem"},
                title="Approximate Number Of Messages",
            ),
            rx.el.th(
                rx.el.div(
                    rx.icon("loader-circle", size=16), class_name="flex justify-center"
                ),
                class_name="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-0",
                style={"width": "1.25rem", "maxWidth": "1.25rem"},
                title="Approximate Number Of Messages Not Visible",
            ),
            rx.el.th(
                rx.el.div(rx.icon("timer", size=16), class_name="flex justify-center"),
                class_name="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider min-w-0",
                style={"width": "1.25rem", "maxWidth": "1.25rem"},
                title="Approximate Number Of Messages Delayed",
            ),
            class_name="bg-slate-50",
        )
    )


def _queue_table(title: str, queue_rows: list[dict[str, str]]) -> rx.Component:
    return rx.el.div(
        rx.el.p(title, class_name="font-semibold text-slate-700 text-sm"),
        rx.el.div(
            rx.el.table(
                rx.el.colgroup(
                    rx.el.col(style={"width": "200px"}),
                    rx.el.col(style={"width": "1.25rem"}),
                    rx.el.col(style={"width": "1.25rem"}),
                    rx.el.col(style={"width": "1.25rem"}),
                ),
                _table_header(),
                rx.el.tbody(rx.foreach(queue_rows, _queue_row), class_name="bg-white"),
                class_name="w-full table-fixed",
            ),
            class_name="rounded-lg border border-slate-200 overflow-hidden",
        ),
        class_name="flex flex-col gap-3 w-full",
    )


def queue_tables() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                rx.el.span("SQS Queue Depths", class_name="text-lg font-semibold text-slate-800"),
                rx.el.span(
                    rx.cond(DashboardState.use_dev_queues, "(dev)", "(prod)"),
                    class_name="text-sm text-slate-500 ml-2",
                ),
                class_name="flex items-center",
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
            _queue_table("Main Queues", DashboardState.queue_rows),
            _queue_table("Dead-Letter Queues", DashboardState.dlq_queue_rows),
            class_name="grid grid-cols-1 gap-6",
        ),
        class_name="p-6 bg-white rounded-2xl border border-slate-200 flex flex-col gap-4",
    )