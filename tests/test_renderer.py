from datetime import datetime

from weather_terminal.models import WeatherPoint
from weather_terminal.renderer import (
    _temperature_axis,
    render_temperature_chart,
)


def make_points(
    *temperatures: float,
) -> list[WeatherPoint]:
    return [
        WeatherPoint(
            time=datetime(
                2026,
                10,
                2,
                index,
            ),
            temperature=temperature,
            precipitation_probability=0,
            weather_code=0,
        )
        for index, temperature in enumerate(
            temperatures
        )
    ]


def test_empty_chart() -> None:
    assert (
        render_temperature_chart([])
        == "No temperature data."
    )


def test_chart_contains_temperature_axis() -> None:
    points = make_points(
        16,
        18,
        20,
        22,
        20,
        18,
    )

    chart = render_temperature_chart(
        points
    )

    assert "° ┤" in chart
    assert "└" in chart


def test_chart_contains_nice_temperature_scale() -> None:
    points = make_points(
        16,
        18,
        20,
        22,
        20,
        18,
    )

    chart = render_temperature_chart(
        points
    )

    assert "24°" in chart
    assert "22°" in chart
    assert "20°" in chart
    assert "18°" in chart
    assert "16°" in chart


def test_chart_contains_braille() -> None:
    points = make_points(
        16,
        18,
        22,
        24,
        21,
        19,
    )

    chart = render_temperature_chart(
        points
    )

    assert any(
        0x2800 <= ord(char) <= 0x28FF
        for char in chart
    )


def test_chart_contains_time_axis() -> None:
    points = make_points(
        16,
        18,
        22,
        24,
        21,
        19,
        18,
        17,
        16,
        18,
        20,
        22,
        24,
        23,
        21,
        19,
        18,
        17,
        16,
        15,
        14,
        15,
        16,
        17,
    )

    chart = render_temperature_chart(
        points
    )

    assert "00" in chart
    assert "04" in chart
    assert "08" in chart
    assert "12" in chart
    assert "16" in chart
    assert "20" in chart


def test_chart_contains_temperature_colors() -> None:
    points = make_points(
        10,
        15,
        20,
        25,
    )

    chart = render_temperature_chart(
        points
    )

    assert "\033[38;2;" in chart
    assert "\033[0m" in chart


def test_chart_respects_requested_width() -> None:
    points = make_points(
        10,
        20,
        15,
        25,
        18,
        22,
    )

    chart = render_temperature_chart(
        points,
        width=20,
        height=8,
    )

    lines = chart.splitlines()

    # A színezés ANSI escape sequence-ei nem
    # számítanak terminálon látható karakternek.
    import re

    ansi_escape = re.compile(
        r"\x1b\[[0-9;]*m"
    )

    visible_line = ansi_escape.sub(
        "",
        lines[0],
    )

    graph_width = len(
        visible_line.split(
            "┤",
            1,
        )[1]
    ) - 1

    assert graph_width == 20


def test_temperature_axis_has_20_percent_padding() -> None:
    minimum, maximum, step = (
        _temperature_axis(
            12,
            24,
        )
    )

    expected_minimum = (
        12 - (24 - 12) * 0.20
    )

    expected_maximum = (
        24 + (24 - 12) * 0.20
    )

    assert minimum <= expected_minimum
    assert maximum >= expected_maximum
