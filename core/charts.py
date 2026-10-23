"""Theme-aware Plotly chart helpers."""

from __future__ import annotations

import plotly.express as px


def template(dark: bool = False) -> str:
    """Select the chart theme to match the app."""
    return "plotly_dark" if dark else "plotly_white"


def risk_donut(data, dark: bool = False):
    """Build a compact risk distribution donut."""
    fig = px.pie(data, names="Risk", values="Students", hole=0.68, color="Risk",
                 color_discrete_map={"High": "#E5484D", "Medium": "#E5A100", "Low": "#22A06B"},
                 template=template(dark))
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        legend_title_text="",
        paper_bgcolor="#0b1220" if dark else "#f4f7fb",
        plot_bgcolor="#131f33" if dark else "#ffffff",
    )
    return fig


def attendance_line(data, dark: bool = False):
    """Build an eight-week attendance trend."""
    fig = px.line(data, x="Week", y="Attendance", markers=True, template=template(dark))
    fig.add_hline(y=75, line_dash="dash", line_color="#E5484D")
    fig.update_layout(
        yaxis_title="Attendance %",
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="#0b1220" if dark else "#f4f7fb",
        plot_bgcolor="#131f33" if dark else "#ffffff",
    )
    return fig
