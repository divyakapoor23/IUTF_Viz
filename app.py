from __future__ import annotations

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from flask import jsonify
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "rainfall_analysis_cloud"
CITIES = [
    "paris",
    "luzern",
    "hamburg",
    "toronto",
    "essen",
    "innsbruck",
    "darmstadt",
    "manchester",
]
NAMES = {city: city.title() for city in CITIES}
NAMES["luzern"] = "Luzern"
RAIN_CLASSES = ["Dry", "Light", "Moderate", "Heavy", "Extreme", "Unknown"]
RAIN_COLORS = {
    "Dry": "#E4F2FF",
    "Light": "#BBD7EF",
    "Moderate": "#81AFD5",
    "Heavy": "#467FB2",
    "Extreme": "#124373",
    "Unknown": "#171717",
}
CITY_COLORS = dict(
    zip(CITIES, ["#0072B2", "#D55E00", "#009E73", "#CC79A7",
                 "#E69F00", "#56B4E9", "#332288", "#666666"])
)
FLOW_COLORSCALE = [
    [0.0, "#B35806"], [0.1, "#D98C3F"], [0.2, "#E5B98C"],
    [0.3, "#F4DDB8"], [0.4, "#FAF2E5"], [0.5, "#F7F7F7"],
    [0.6, "#D9EAF7"], [0.7, "#A7CDE3"], [0.8, "#67A9CF"],
    [0.9, "#3282BD"], [1.0, "#2166AC"],
]
MIN_SUPPORTED_HOURS = 10
MIN_SUPPORTED_DATES = 3
BINS = [0, 0.1, 0.5, 4, 10, np.inf]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hours = pd.read_csv(DATA_DIR / "city_hour_summary.csv")
    events = pd.read_csv(DATA_DIR / "rain_events.csv")
    curves = pd.read_csv(DATA_DIR / "recovery_curves.csv")

    hours["timestamp"] = pd.to_datetime(hours["timestamp"], errors="raise")
    hours["date"] = pd.to_datetime(hours["date"], errors="raise")
    hours["rain_mm"] = pd.to_numeric(hours["rain_mm"], errors="coerce")
    hours["median_flow_change_pct"] = pd.to_numeric(
        hours["median_flow_change_pct"], errors="coerce"
    )
    events["start"] = pd.to_datetime(events["start"], errors="raise")
    events["peak_rain_mm"] = pd.to_numeric(events["peak_rain_mm"], errors="coerce")
    events["minimum_wet_flow_change_pct"] = pd.to_numeric(
        events["minimum_wet_flow_change_pct"], errors="coerce"
    )
    events["recovery_confirmed_hours"] = pd.to_numeric(
        events["recovery_confirmed_hours"], errors="coerce"
    )
    events["flow_deficit_observed"] = (
        events["flow_deficit_observed"].astype(str).str.lower().eq("true")
    )
    curves["hours_from_rain_end"] = pd.to_numeric(
        curves["hours_from_rain_end"], errors="raise"
    )
    curves["flow_change_pct"] = pd.to_numeric(
        curves["flow_change_pct"], errors="coerce"
    )
    return hours, events, curves


HOURS, EVENTS, CURVES = load_data()
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server


@server.get("/healthz")
def health_check():
    return jsonify(status="ok")


def empty_figure(message: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper"
    )
    figure.update_layout(template="plotly_white", height=430)
    return figure


def make_coverage_chart(hours: pd.DataFrame) -> go.Figure:
    if hours.empty:
        return empty_figure("No observed hours for the selected filters.")
    counts = (
        hours.assign(rain_bin=hours["rain_bin"].fillna("Unknown"))
        .groupby(["city", "rain_bin"], observed=True)
        .size()
        .unstack(fill_value=0)
        .reindex(index=CITIES, columns=RAIN_CLASSES, fill_value=0)
    )
    figure = go.Figure()
    for rain_class in RAIN_CLASSES:
        figure.add_bar(
            name=rain_class,
            y=[NAMES[city] for city in counts.index],
            x=counts[rain_class],
            orientation="h",
            marker={
                "color": RAIN_COLORS[rain_class],
                "pattern": {"shape": {"Dry": ".", "Unknown": "/"}.get(rain_class, "")},
            },
            hovertemplate="%{y}<br>" + rain_class + ": %{x:,} city-hours<extra></extra>",
        )
    figure.update_layout(
        barmode="stack",
        title="Rainfall coverage by city",
        xaxis_title="Observed city-hours",
        yaxis={"autorange": "reversed"},
        legend_title="Hourly rainfall",
        height=470,
        margin={"l": 100, "r": 30, "t": 80, "b": 55},
    )
    return figure


def summarize_intensity(hours: pd.DataFrame) -> pd.DataFrame:
    observed = (
        hours[hours["rain_bin"].notna()]
        .groupby(["city", "rain_bin"], observed=True)
        .agg(
            observed_hours=("timestamp", "nunique"),
            observed_dates=("date", "nunique"),
        )
        .reset_index()
    )
    supported = (
        hours[hours["median_flow_change_pct"].notna() & hours["rain_bin"].notna()]
        .groupby(["city", "rain_bin"], observed=True)
        .agg(
            median_change_pct=("median_flow_change_pct", "median"),
            supported_hours=("timestamp", "nunique"),
            supported_dates=("date", "nunique"),
        )
        .reset_index()
    )
    result = observed.merge(
        supported, on=["city", "rain_bin"], how="left", validate="one_to_one"
    )
    result["supported_hours"] = result["supported_hours"].fillna(0).astype(int)
    result["supported_dates"] = result["supported_dates"].fillna(0).astype(int)
    result["eligible"] = (
        result["supported_hours"].ge(MIN_SUPPORTED_HOURS)
        & result["supported_dates"].ge(MIN_SUPPORTED_DATES)
    )
    result["median_change_pct"] = result["median_change_pct"].where(result["eligible"])
    return result


def make_intensity_chart(hours: pd.DataFrame) -> go.Figure:
    if hours.empty:
        return empty_figure("No observed hours for the selected filters.")
    summary = summarize_intensity(hours)
    matrix = summary.pivot(
        index="city", columns="rain_bin", values="median_change_pct"
    ).reindex(index=CITIES, columns=RAIN_CLASSES[:-1])
    support = summary.pivot(
        index="city", columns="rain_bin", values="supported_hours"
    ).reindex(index=CITIES, columns=RAIN_CLASSES[:-1]).fillna(0)
    dates = summary.pivot(
        index="city", columns="rain_bin", values="supported_dates"
    ).reindex(index=CITIES, columns=RAIN_CLASSES[:-1]).fillna(0)
    values = matrix.to_numpy(dtype=float)
    limit = max(10.0, float(np.nanmax(np.abs(values))) if np.isfinite(values).any() else 10.0)
    labels = []
    for city in CITIES:
        row = []
        for rain_class in RAIN_CLASSES[:-1]:
            value = matrix.loc[city, rain_class]
            if pd.isna(value):
                row.append(
                    "No rain hours"
                    if hours.loc[
                        hours["city"].eq(city) & hours["rain_bin"].eq(rain_class)
                    ].empty
                    else f"Insufficient support<br>{int(support.loc[city, rain_class])} h, "
                    f"{int(dates.loc[city, rain_class])} dates"
                )
            else:
                row.append(
                    f"{value:+.1f}%<br>n={int(support.loc[city, rain_class])} h"
                )
        labels.append(row)
    figure = go.Figure(
        go.Heatmap(
            z=values,
            x=RAIN_CLASSES[:-1],
            y=[NAMES[city] for city in CITIES],
            text=labels,
            texttemplate="%{text}",
            customdata=np.stack(
                [support.to_numpy(), dates.to_numpy()], axis=-1
            ),
            hovertemplate=(
                "%{y} · %{x}<br>Median flow change: %{z:+.2f}%"
                "<br>Supported hours: %{customdata[0]}"
                "<br>Supported dates: %{customdata[1]}<extra></extra>"
            ),
            colorscale=FLOW_COLORSCALE,
            zmin=-limit,
            zmax=limit,
            zmid=0,
            colorbar={"title": "Median flow<br>change (%)"},
            xgap=2,
            ygap=2,
        )
    )
    for city, rain_class, label in (
        ("innsbruck", "Dry", "Dry reference"),
        ("luzern", "Heavy", "Heavy rain"),
    ):
        if pd.notna(matrix.loc[city, rain_class]):
            figure.add_annotation(
                x=rain_class, y=NAMES[city], text=label, showarrow=True,
                ax=0, ay=-34, standoff=9, arrowhead=2,
                arrowcolor="#222222", bgcolor="rgba(255,255,255,.94)",
                font={"size": 9, "color": "#222222"},
            )
    figure.update_layout(
        title="Median flow change by hourly rainfall intensity",
        xaxis_title="Hourly rainfall class",
        yaxis={"autorange": "reversed", "title": ""},
        height=530,
        margin={"l": 100, "r": 40, "t": 80, "b": 65},
    )
    return figure


def make_hourly_chart(hours: pd.DataFrame) -> go.Figure:
    supported = hours.dropna(subset=["rain_bin", "median_flow_change_pct"]).copy()
    if supported.empty:
        return empty_figure("No supported flow observations for the selected filters.")
    supported["hour_of_day"] = supported["timestamp"].dt.hour
    supported["condition"] = np.where(supported["rain_bin"].eq("Dry"), "Dry", "Rainy")
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.1,
        subplot_titles=("Median flow deviation", "Supported city-hours"),
    )
    for city in CITIES:
        subset = supported[supported["city"].eq(city)]
        if subset.empty:
            continue
        for condition, color, dash, marker in (
            ("Dry", "#64748B", "dash", "circle-open"),
            ("Rainy", "#1768AC", "solid", "diamond"),
        ):
            group = subset[subset["condition"].eq(condition)]
            summary = group.groupby("hour_of_day")["median_flow_change_pct"].agg(
                median="median", count="size"
            ).reindex(range(24))
            figure.add_trace(
                go.Scatter(
                    x=list(range(24)),
                    y=summary["median"],
                    customdata=summary["count"].fillna(0),
                    mode="lines+markers",
                    name=f"{NAMES[city]} · {condition}",
                    legendgroup=city,
                    line={"color": CITY_COLORS[city], "dash": dash},
                    marker={"symbol": marker, "color": CITY_COLORS[city], "size": 6},
                    hovertemplate=(
                        f"{NAMES[city]} · {condition}<br>%{{x:02d}}:00"
                        "<br>Median: %{y:+.2f}%<br>City-hours: %{customdata:.0f}<extra></extra>"
                    ),
                ),
                row=1,
                col=1,
            )
            counts = group.groupby("hour_of_day").size().reindex(range(24), fill_value=0)
            figure.add_trace(
                go.Bar(
                    x=list(range(24)),
                    y=counts,
                    name=f"{NAMES[city]} · {condition} count",
                    marker_color=CITY_COLORS[city],
                    opacity=0.72 if condition == "Dry" else 0.4,
                    showlegend=False,
                    hovertemplate="%{x:02d}:00<br>City-hours: %{y}<extra></extra>",
                ),
                row=2,
                col=1,
            )
    figure.update_layout(
        title="Traffic patterns by hour of day",
        height=580,
        barmode="group",
        legend={"orientation": "h", "y": 1.12},
        margin={"l": 65, "r": 25, "t": 125, "b": 55},
    )
    figure.update_xaxes(title_text="Recorded hour of day", dtick=2, row=2, col=1)
    figure.update_yaxes(title_text="Median flow change (%)", row=1, col=1)
    figure.update_yaxes(title_text="City-hours", rangemode="tozero", row=2, col=1)
    return figure


def make_storm_chart(events: pd.DataFrame) -> go.Figure:
    if events.empty:
        return empty_figure("No qualifying rain events for the selected filters.")
    figure = go.Figure()
    for city in CITIES:
        subset = events[events["city"].eq(city)]
        if subset.empty:
            continue
        figure.add_trace(
            go.Scatter(
                x=subset["peak_rain_mm"],
                y=subset["minimum_wet_flow_change_pct"],
                mode="markers",
                name=NAMES[city],
                marker={"color": CITY_COLORS[city], "size": 10, "opacity": 0.8},
                customdata=np.stack(
                    [subset["event_id"], subset["duration_hours"]], axis=-1
                ),
                hovertemplate=(
                    f"{NAMES[city]}<br>Peak rain: %{{x:.2f}} mm/h"
                    "<br>Lowest flow deviation: %{y:+.1f}%"
                    "<br>Duration: %{customdata[1]} h"
                    "<br>Event: %{customdata[0]}<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        title="Storm intensity vs. traffic disruption",
        xaxis_title="Peak hourly rainfall per event (mm/hour)",
        yaxis_title="Lowest flow deviation during rain (%)",
        height=500,
        margin={"l": 75, "r": 30, "t": 80, "b": 65},
        legend={"orientation": "h"},
    )
    return figure


def make_recovery_chart(
    events: pd.DataFrame, curves: pd.DataFrame, cities: list[str]
) -> go.Figure:
    if curves.empty:
        return empty_figure("No recovery observations for the selected filters.")
    rows = max(1, (len(cities) + 1) // 2)
    figure = make_subplots(
        rows=rows,
        cols=2,
        subplot_titles=[
            f"{NAMES[city]} · "
            f"{events.loc[events['city'].eq(city), 'event_id'].nunique()} events"
            for city in cities
        ],
        horizontal_spacing=0.08,
        vertical_spacing=0.12,
    )
    for index, city in enumerate(cities):
        row, col = divmod(index, 2)
        row += 1
        col += 1
        city_curves = curves[curves["city"].eq(city)]
        summary = city_curves.groupby("hours_from_rain_end")["flow_change_pct"].agg(
            median="median",
            q25=lambda values: values.quantile(0.25),
            q75=lambda values: values.quantile(0.75),
            events="count",
        )
        x = summary.index
        figure.add_trace(
            go.Scatter(
                x=x,
                y=summary["q25"],
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            ),
            row=row,
            col=col,
        )
        figure.add_trace(
            go.Scatter(
                x=x,
                y=summary["q75"],
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor="rgba(0,90,156,.18)",
                name="Middle 50% of events",
                showlegend=index == 0,
                hoverinfo="skip",
            ),
            row=row,
            col=col,
        )
        figure.add_trace(
            go.Scatter(
                x=x,
                y=summary["median"],
                mode="lines+markers",
                line={"color": "#005A9C"},
                marker={"size": 5},
                name="Event median",
                showlegend=index == 0,
                customdata=summary["events"],
                hovertemplate=(
                    "Hour %{x}<br>Median: %{y:+.1f}%"
                    "<br>Events: %{customdata}<extra></extra>"
                ),
            ),
            row=row,
            col=col,
        )
        figure.add_hline(y=0, line_dash="dash", line_color="#555", row=row, col=col)
        figure.add_vline(x=0, line_dash="dot", line_color="#555", row=row, col=col)
    figure.update_layout(
        title="Traffic flow after rain ends",
        height=max(550, 290 * rows),
        margin={"l": 65, "r": 25, "t": 100, "b": 65},
        legend={"orientation": "h", "y": -0.08},
    )
    figure.update_xaxes(title_text="Hours from rain ending (0 = first dry hour)")
    figure.update_yaxes(title_text="Flow change from dry baseline (%)")
    return figure


def filter_data(
    selected_cities: list[str], day_type: str, intensity: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hours = HOURS[HOURS["city"].isin(selected_cities)].copy()
    events = EVENTS[EVENTS["city"].isin(selected_cities)].copy()
    if day_type == "weekday":
        hours = hours[hours["timestamp"].dt.dayofweek < 5]
        events = events[events["start"].dt.dayofweek < 5]
    elif day_type == "weekend":
        hours = hours[hours["timestamp"].dt.dayofweek >= 5]
        events = events[events["start"].dt.dayofweek >= 5]
    if intensity not in ("all", "unknown"):
        hours = hours[hours["rain_bin"].eq(intensity)]
        peak_bins = pd.cut(
            events["peak_rain_mm"], bins=BINS, labels=RAIN_CLASSES[:-1], right=False
        )
        events = events[peak_bins.eq(intensity)]
    elif intensity == "unknown":
        hours = hours[hours["rain_bin"].isna()]
        events = events.iloc[0:0]
    curves = CURVES[CURVES["event_id"].isin(events["event_id"])].copy()
    return hours, events, curves


app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.Header(
                    [
                        html.P(
                            "IUTF | RAINFALL + URBAN TRAFFIC",
                            className="mb-2",
                            style={"color": "#E5EEE5", "fontWeight": "700"},
                        ),
                        html.H1(
                            "Rainfall & Traffic Flow Across Eight Cities",
                            style={"color": "#FFFDF6", "fontWeight": "750"},
                        ),
                        html.P(
                            "Explore rainfall coverage, traffic-flow deviations, storm events, and recovery.",
                            className="mb-0",
                            style={"color": "#F1F4EC"},
                        ),
                    ],
                    className="p-4 p-lg-5",
                    style={"backgroundColor": "#365A49", "borderRadius": "18px"},
                ),
                width=12,
            ),
            className="pt-4 pb-3",
        ),
        dbc.Card(
            dbc.CardBody(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Cities"),
                                dcc.Dropdown(
                                    id="cities",
                                    options=[
                                        {"label": NAMES[city], "value": city}
                                        for city in CITIES
                                    ],
                                    value=CITIES,
                                    multi=True,
                                ),
                            ],
                            xs=12,
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label("Day type"),
                                dcc.Dropdown(
                                    id="day-type",
                                    options=[
                                        {"label": "All days", "value": "all"},
                                        {"label": "Weekdays", "value": "weekday"},
                                        {"label": "Weekends", "value": "weekend"},
                                    ],
                                    value="all",
                                    clearable=False,
                                ),
                            ],
                            xs=12,
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label("Rainfall intensity"),
                                dcc.Dropdown(
                                    id="intensity",
                                    options=[
                                        {"label": "All intensities", "value": "all"},
                                        *[
                                            {"label": label, "value": label}
                                            for label in RAIN_CLASSES[:-1]
                                        ],
                                        {"label": "Unknown rainfall", "value": "unknown"},
                                    ],
                                    value="all",
                                    clearable=False,
                                ),
                            ],
                            xs=12,
                            md=4,
                        ),
                    ],
                    className="g-3",
                ),
            ),
            className="mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Card(dbc.CardBody([html.Div("Selected cities"), html.H2(id="kpi-cities")])), xs=12, sm=6, lg=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.Div("Observed city-hours"), html.H2(id="kpi-hours")])), xs=12, sm=6, lg=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.Div("Qualifying rain events"), html.H2(id="kpi-events")])), xs=12, sm=6, lg=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.Div("Confirmed recoveries"), html.H2(id="kpi-recovery")])), xs=12, sm=6, lg=3),
            ],
            className="g-3 mb-4",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="coverage"), xs=12, lg=5),
                dbc.Col(dcc.Graph(id="intensity-chart"), xs=12, lg=7),
            ],
            className="g-3 mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="hourly"), xs=12, lg=6),
                dbc.Col(dcc.Graph(id="storm"), xs=12, lg=6),
            ],
            className="g-3 mb-3",
        ),
        dbc.Row(dbc.Col(dcc.Graph(id="recovery"), width=12), className="mb-3"),
        html.Footer(
            [
                "Precomputed analysis data · ",
                html.A(
                    "Project source and methodology",
                    href="https://github.com/divyakapoor23/IUTF_Viz",
                    target="_blank",
                    rel="noopener noreferrer",
                ),
                html.P(
                    "Weather matches have known limitations. Results describe observed associations, not causal effects.",
                    className="mt-2 mb-0",
                ),
            ],
            className="text-center py-3",
        ),
    ],
    fluid=True,
    className="px-3 px-lg-4 pb-4",
    style={
        "backgroundColor": "#F4F4EB",
        "minHeight": "100vh",
        "maxWidth": "1680px",
        "margin": "0 auto",
    },
)


@app.callback(
    [
        Output("kpi-cities", "children"),
        Output("kpi-hours", "children"),
        Output("kpi-events", "children"),
        Output("kpi-recovery", "children"),
        Output("coverage", "figure"),
        Output("intensity-chart", "figure"),
        Output("hourly", "figure"),
        Output("storm", "figure"),
        Output("recovery", "figure"),
    ],
    [
        Input("cities", "value"),
        Input("day-type", "value"),
        Input("intensity", "value"),
    ],
)
def update_dashboard(
    selected_cities: list[str] | None, day_type: str, intensity: str
):
    cities = [city for city in (selected_cities or []) if city in CITIES]
    if not cities:
        message = empty_figure("Select at least one city to display data.")
        return "0", "0", "0", "0 / 0", message, message, message, message, message

    hours, events, curves = filter_data(cities, day_type, intensity)
    deficits = events[events["flow_deficit_observed"]]
    confirmed = deficits["recovery_confirmed_hours"].notna().sum()
    return (
        str(len(cities)),
        f"{len(hours):,}",
        f"{len(events):,}",
        f"{confirmed:,} / {len(deficits):,}",
        make_coverage_chart(hours),
        make_intensity_chart(hours),
        make_hourly_chart(hours),
        make_storm_chart(events),
        make_recovery_chart(events, curves, cities),
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
