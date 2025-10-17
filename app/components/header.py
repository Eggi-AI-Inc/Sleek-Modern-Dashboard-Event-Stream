import reflex as rx
from app.states.dashboard_state import DashboardState


def stat_card(icon: str, title: str, value: rx.Var[int], color: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                icon,
                size=24,
                class_name=rx.match(
                    color,
                    ("indigo", "text-indigo-500"),
                    ("green", "text-green-500"),
                    ("yellow", "text-yellow-500"),
                    ("red", "text-red-500"),
                    "text-slate-500",
                ),
            ),
            class_name=rx.match(
                color,
                ("indigo", "p-3 bg-indigo-100 rounded-lg"),
                ("green", "p-3 bg-green-100 rounded-lg"),
                ("yellow", "p-3 bg-yellow-100 rounded-lg"),
                ("red", "p-3 bg-red-100 rounded-lg"),
                "p-3 bg-slate-100 rounded-lg",
            ),
        ),
        rx.el.div(
            rx.el.p(title, class_name="text-sm font-medium text-slate-500"),
            rx.el.p(
                value, class_name="text-3xl font-bold text-slate-800 tracking-tight"
            ),
            class_name="flex flex-col",
        ),
        class_name="flex items-center gap-4 p-6 bg-white rounded-2xl border border-slate-200 hover:border-indigo-300 transition-colors",
    )


def header() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            rx.el.div(
                rx.icon("egg-fried", size=32, class_name="text-indigo-600"),
                rx.el.h1("Eggi.io", class_name="text-2xl font-bold text-slate-800"),
                class_name="flex items-center gap-3",
            ),
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    checked=DashboardState.use_dev_queues,
                    on_change=DashboardState.set_use_dev_queues,
                    class_name="sr-only peer",
                ),
                rx.el.div(
                    class_name="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600 relative",
                ),
                rx.el.span(
                    rx.cond(
                        DashboardState.use_dev_queues,
                        "Dev queues",
                        "Prod queues",
                    ),
                    class_name="ml-3 text-sm font-medium text-slate-600",
                ),
                class_name="inline-flex items-center cursor-pointer select-none",
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.div(
            rx.el.h1("Live Dashboard", class_name="text-3xl font-bold text-slate-800"),
            rx.el.p(
                "Real-time system monitoring and event tracking.",
                class_name="text-slate-500",
            ),
            class_name="flex flex-col gap-2",
        ),
        rx.el.div(
            stat_card(
                "activity", "Total Events", DashboardState.stats["total"], "indigo"
            ),
            stat_card("square-check", "Success", DashboardState.stats["ok"], "green"),
            stat_card(
                "flag-triangle-right",
                "Warnings",
                DashboardState.stats["warn"],
                "yellow",
            ),
            stat_card("circle-x", "Errors", DashboardState.stats["error"], "red"),
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6",
        ),
        class_name="flex flex-col gap-6",
    )