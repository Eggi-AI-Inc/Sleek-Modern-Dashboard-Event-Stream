import reflex as rx
from app.states.dashboard_state import DashboardState


def live_chart() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                "API Request Volume", class_name="text-lg font-semibold text-slate-800"
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
        rx.recharts.area_chart(
            rx.recharts.cartesian_grid(
                horizontal=True, vertical=False, class_name="stroke-slate-200"
            ),
            rx.el.svg.defs(
                rx.el.svg.linear_gradient(
                    rx.el.svg.stop(offset="5%", stop_color="#8B5CF6", stop_opacity=0.4),
                    rx.el.svg.stop(
                        offset="95%", stop_color="#6366F1", stop_opacity=0.1
                    ),
                    id="chart_gradient",
                    x1="0",
                    y1="0",
                    x2="0",
                    y2="1",
                )
            ),
            rx.recharts.x_axis(data_key="time", hide=True),
            rx.recharts.y_axis(domain=[0, "dataMax + 50"], hide=True),
            rx.recharts.tooltip(
                cursor=False,
                content_style={
                    "background": "white",
                    "border": "1px solid #e2e8f0",
                    "borderRadius": "0.75rem",
                },
            ),
            rx.recharts.area(
                data_key="value",
                type_="natural",
                stroke="#6366F1",
                fill="url(#chart_gradient)",
                stroke_width=2,
                dot=False,
            ),
            data=DashboardState.chart_data,
            height=350,
            width="100%",
        ),
        class_name="p-6 bg-white rounded-2xl border border-slate-200 flex flex-col gap-4",
    )