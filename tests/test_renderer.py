from datetime import datetime

from weather_terminal.models import WeatherPoint
from weather_terminal.renderer import render_temperature_chart


def make_points(*temperatures: float) -> list[WeatherPoint]:
    return [
        WeatherPoint(
            time=datetime(2026, 10, 2, index),
            temperature=temperature,
            precipitation_probability=0,
            weather_code=0,
        )
        for index, temperature in enumerate(temperatures)
    ]


def test_empty_chart() -> None:
    assert render_temperature_chart([]) == "No temperature data."


def test_chart_contains_temperature_axis() -> None:
    points = make_points(16, 18, 20, 22, 20, 18)

    chart = render_temperature_chart(points)

    assert "° ┤" in chart
    assert "└" in chart
    assert "●" in chart


def test_chart_respects_width() -> None:
    points = make_points(10, 20, 15, 25, 18, 22)

    chart = render_temperature_chart(
        points,
        width=4,
    )

    graph_lines = chart.splitlines()[:-1]

    for line in graph_lines:
        graph = line.split("┤", 1)[1]
        assert len(graph) == 4
