import reflex as rx
from app.components.header import header
from app.components.live_chart import live_chart
from app.components.event_stream import event_stream
from app.states.dashboard_state import DashboardState


def index() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            rx.el.div(
                header(), live_chart(), class_name="flex flex-col gap-6 w-full lg:w-2/3"
            ),
            event_stream(),
            class_name="flex flex-col lg:flex-row gap-6 p-6",
        ),
        class_name="bg-slate-50 font-['Inter'] min-h-screen",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(
    index, title="Eggi.io Dashboard", on_load=DashboardState.start_streaming_on_load
)