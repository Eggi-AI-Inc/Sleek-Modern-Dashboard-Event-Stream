import reflex as rx
from app.states.dashboard_state import DashboardState


def stat_card(icon: str, title: str, value: rx.Var[int], color: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, size=24, class_name=f"text-{color}-500"),
            class_name=f"p-3 bg-{color}-100 rounded-lg",
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
            rx.el.h1("Live Dashboard", class_name="text-3xl font-bold text-slate-800"),
            rx.el.p(
                "Real-time system monitoring and event tracking.",
                class_name="text-slate-500",
            ),
        ),
        rx.el.div(
            stat_card(
                "activity", "Total Events", DashboardState.stats["total"], "indigo"
            ),
            stat_card("square_check", "Success", DashboardState.stats["ok"], "green"),
            stat_card(
                "flag_triangle_right",
                "Warnings",
                DashboardState.stats["warn"],
                "yellow",
            ),
            stat_card("circle_x", "Errors", DashboardState.stats["error"], "red"),
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6",
        ),
        class_name="flex flex-col gap-6",
    )