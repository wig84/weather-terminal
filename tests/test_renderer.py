from datetime import datetime

from weather_terminal.models import WeatherPoint
from weather_terminal.renderer import (
    _temperature_axis,
    render_precipitation_chart,
    render_temperature_chart,
    render_weather_strip,
    weather_color,
    weather_symbol,
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


def make_weather_points(
    *weather_codes: int,
) -> list[WeatherPoint]:
    return [
        WeatherPoint(
            time=datetime(
                2026,
                10,
                2,
                index,
            ),
            temperature=20.0,
            precipitation_probability=0,
            weather_code=weather_code,
        )
        for index, weather_code in enumerate(
            weather_codes
        )
    ]


def make_precipitation_points(
    *probabilities: int,
) -> list[WeatherPoint]:
    return [
        WeatherPoint(
            time=datetime(
                2026,
                10,
                2,
                index,
            ),
            temperature=20.0,
            precipitation_probability=probability,
            weather_code=61,
        )
        for index, probability in enumerate(
            probabilities
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


def test_chart_renders_all_graph_rows() -> None:
    points = make_points(
        14,
        15,
        16,
        18,
        21,
        23,
        24,
        23,
        21,
        19,
        17,
        15,
    )

    chart = render_temperature_chart(
        points,
        width=20,
        height=10,
    )

    lines = chart.splitlines()

    bottom_index = next(
        index
        for index, line in enumerate(lines)
        if "└" in line
    )

    graph_lines = lines[
        :bottom_index
    ]

    expected_graph_height = (
        (10 * 4 + 3) // 4
    )

    assert len(graph_lines) == (
        expected_graph_height
    )


def test_chart_contains_lower_temperature_data() -> None:
    points = make_points(
        14,
        15,
        16,
        18,
        21,
        23,
        24,
        23,
        21,
        19,
        17,
        15,
    )

    chart = render_temperature_chart(
        points,
        width=20,
        height=10,
    )

    lines = chart.splitlines()

    bottom_index = next(
        index
        for index, line in enumerate(lines)
        if "└" in line
    )

    graph_lines = lines[
        :bottom_index
    ]

    lower_half = graph_lines[
        len(graph_lines) // 2 :
    ]

    assert any(
        0x2800 <= ord(char) <= 0x28FF
        for line in lower_half
        for char in line
    )


def test_weather_symbol_clear_sky() -> None:
    assert weather_symbol(0) == "☀"


def test_weather_symbol_clouds() -> None:
    assert weather_symbol(1) == "🌤"
    assert weather_symbol(2) == "🌤"
    assert weather_symbol(3) == "☁"


def test_weather_symbol_rain() -> None:
    assert weather_symbol(61) == "🌧"
    assert weather_symbol(63) == "🌧"
    assert weather_symbol(65) == "🌧"


def test_weather_symbol_snow() -> None:
    assert weather_symbol(71) == "🌨"
    assert weather_symbol(73) == "🌨"
    assert weather_symbol(75) == "🌨"


def test_weather_symbol_thunderstorm() -> None:
    assert weather_symbol(95) == "⛈"
    assert weather_symbol(99) == "⛈"


def test_weather_symbol_unknown() -> None:
    assert weather_symbol(None) == "?"
    assert weather_symbol(999) == "?"


def test_weather_color_clear_sky() -> None:
    assert weather_color(0) == (
        255,
        210,
        40,
    )


def test_weather_color_rain() -> None:
    assert weather_color(61) == (
        60,
        150,
        255,
    )


def test_weather_color_thunderstorm() -> None:
    assert weather_color(95) == (
        190,
        120,
        255,
    )


def test_weather_strip_contains_symbols() -> None:
    weather_codes = [0] * 24

    weather_codes[0] = 0
    weather_codes[4] = 1
    weather_codes[8] = 3
    weather_codes[12] = 61
    weather_codes[16] = 95
    weather_codes[20] = 71

    points = make_weather_points(
        *weather_codes
    )

    weather = render_weather_strip(
        points,
        width=32,
    )

    assert "☀" in weather
    assert "🌤" in weather
    assert "☁" in weather
    assert "🌧" in weather
    assert "⛈" in weather
    assert "🌨" in weather


def test_weather_strip_contains_time_axis() -> None:
    points = make_weather_points(
        *([0] * 24)
    )

    weather = render_weather_strip(
        points,
        width=32,
    )

    assert "00" in weather
    assert "04" in weather
    assert "08" in weather
    assert "12" in weather
    assert "16" in weather
    assert "20" in weather


def test_weather_strip_contains_colors() -> None:
    weather_codes = [0] * 24

    weather_codes[0] = 0
    weather_codes[4] = 3
    weather_codes[8] = 61
    weather_codes[12] = 71
    weather_codes[16] = 95
    weather_codes[20] = 45

    points = make_weather_points(
        *weather_codes
    )

    weather = render_weather_strip(
        points,
        width=32,
    )

    assert "\033[38;2;" in weather
    assert "\033[0m" in weather


def test_precipitation_chart_contains_bars() -> None:
    points = make_precipitation_points(
        0,
        0,
        0,
        0,
        25,
        25,
        50,
        50,
        75,
        75,
        100,
        100,
    )

    chart = render_precipitation_chart(
        points,
        width=32,
        height=6,
    )

    assert "█" in chart
    assert "100%" in chart
    assert "80%" in chart
    assert "60%" in chart
    assert "40%" in chart
    assert "20%" in chart
    assert "0%" in chart
    assert "─" in chart
    assert "no rain today" not in chart


def test_precipitation_chart_contains_time_axis() -> None:
    points = make_precipitation_points(
        *([0] * 24)
    )

    chart = render_precipitation_chart(
        points,
        width=32,
        height=6,
    )

    assert "00" in chart
    assert "04" in chart
    assert "08" in chart
    assert "12" in chart
    assert "16" in chart
    assert "20" in chart


def test_precipitation_chart_empty_data() -> None:
    assert (
        render_precipitation_chart([])
        == "No precipitation data."
    )


def test_precipitation_chart_no_rain_message() -> None:
    points = make_precipitation_points(
        *([0] * 24)
    )

    chart = render_precipitation_chart(
        points,
        width=32,
        height=6,
    )

    assert "no rain today" in chart
    assert "100%" in chart
    assert "80%" in chart
    assert "60%" in chart
    assert "40%" in chart
    assert "20%" in chart
    assert "0%" in chart
