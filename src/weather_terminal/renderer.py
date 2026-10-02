from collections.abc import Sequence

from .models import WeatherPoint


_BRAILLE_DOTS = {
    (0, 0): 0x01,
    (0, 1): 0x02,
    (0, 2): 0x04,
    (1, 0): 0x08,
    (1, 1): 0x10,
    (1, 2): 0x20,
    (0, 3): 0x40,
    (1, 3): 0x80,
}

_RESET = "\033[0m"


def _braille_char(
    pixels: set[tuple[int, int]],
) -> str:
    value = 0

    for x, y in pixels:
        value |= _BRAILLE_DOTS[(x, y)]

    return chr(0x2800 + value)


def _interpolate(
    values: Sequence[float],
    width: int,
) -> list[float]:
    if not values:
        return []

    if width <= 1 or len(values) == 1:
        return [values[0]] * width

    if len(values) == width:
        return list(values)

    result: list[float] = []

    for x in range(width):
        position = (
            x * (len(values) - 1)
            / (width - 1)
        )

        left = int(position)
        right = min(
            left + 1,
            len(values) - 1,
        )

        fraction = position - left

        value = (
            values[left]
            + (
                values[right]
                - values[left]
            )
            * fraction
        )

        result.append(value)

    return result


def _nice_step(
    data_range: float,
    target_steps: int = 5,
) -> float:
    if data_range <= 0:
        return 1.0

    rough_step = data_range / target_steps

    candidates = (
        1.0,
        2.0,
        5.0,
        10.0,
    )

    import math

    magnitude = 10 ** int(
        math.floor(
            math.log10(rough_step)
        )
    )

    normalized = rough_step / magnitude

    for candidate in candidates:
        if normalized <= candidate:
            return candidate * magnitude

    return 10.0 * magnitude


def _temperature_axis(
    minimum: float,
    maximum: float,
    *,
    target_steps: int = 5,
) -> tuple[float, float, float]:
    import math

    data_range = maximum - minimum

    if data_range == 0:
        data_range = 2.0

    padding = data_range * 0.20

    padded_minimum = minimum - padding
    padded_maximum = maximum + padding

    padded_range = (
        padded_maximum
        - padded_minimum
    )

    step = _nice_step(
        padded_range,
        target_steps,
    )

    axis_min = (
        math.floor(
            padded_minimum / step
        )
        * step
    )

    axis_max = (
        math.ceil(
            padded_maximum / step
        )
        * step
    )

    if axis_min == axis_max:
        axis_max += step

    return axis_min, axis_max, step


def _plot_line(
    values: Sequence[float],
    *,
    pixel_width: int,
    pixel_height: int,
    minimum: float,
    maximum: float,
) -> set[tuple[int, int]]:
    pixels: set[tuple[int, int]] = set()

    if not values:
        return pixels

    value_range = maximum - minimum

    if value_range == 0:
        value_range = 1.0

    previous_y: int | None = None

    for x, value in enumerate(values):
        normalized = (
            (value - minimum)
            / value_range
        )

        y = round(
            (1.0 - normalized)
            * (pixel_height - 1)
        )

        pixels.add((x, y))

        if previous_y is not None:
            start_y = min(
                previous_y,
                y,
            )

            end_y = max(
                previous_y,
                y,
            )

            for interpolated_y in range(
                start_y,
                end_y + 1,
            ):
                pixels.add(
                    (
                        x - 1,
                        interpolated_y,
                    )
                )

                pixels.add(
                    (
                        x,
                        interpolated_y,
                    )
                )

        previous_y = y

    return pixels


def _temperature_color(
    temperature: float,
    *,
    minimum: float,
    maximum: float,
) -> tuple[int, int, int]:
    if maximum <= minimum:
        normalized = 0.5
    else:
        normalized = (
            temperature - minimum
        ) / (maximum - minimum)

    normalized = max(
        0.0,
        min(1.0, normalized),
    )

    stops = (
        (0.00, (50, 110, 255)),
        (0.25, (0, 210, 255)),
        (0.50, (50, 210, 100)),
        (0.70, (255, 220, 50)),
        (0.85, (255, 150, 30)),
        (1.00, (255, 70, 70)),
    )

    for index in range(
        len(stops) - 1
    ):
        left_position, left_color = (
            stops[index]
        )

        right_position, right_color = (
            stops[index + 1]
        )

        if normalized <= right_position:
            fraction = (
                normalized - left_position
            ) / (
                right_position
                - left_position
            )

            return tuple(
                round(
                    left_color[channel]
                    + (
                        right_color[channel]
                        - left_color[channel]
                    )
                    * fraction
                )
                for channel in range(3)
            )

    return stops[-1][1]


def _ansi_color(
    temperature: float,
    *,
    minimum: float,
    maximum: float,
) -> str:
    red, green, blue = _temperature_color(
        temperature,
        minimum=minimum,
        maximum=maximum,
    )

    return (
        f"\033[38;2;"
        f"{red};{green};{blue}m"
    )


def _render_braille(
    pixels: set[tuple[int, int]],
    values: Sequence[float],
    *,
    pixel_width: int,
    pixel_height: int,
    minimum: float,
    maximum: float,
) -> list[str]:
    char_width = (
        pixel_width + 1
    ) // 2

    char_height = (
        pixel_height + 3
    ) // 4

    lines: list[str] = []

    for char_y in range(char_height):
        line = ""

        for char_x in range(char_width):
            dots: set[tuple[int, int]] = set()

            for local_x in range(2):
                for local_y in range(4):
                    pixel_x = (
                        char_x * 2
                        + local_x
                    )

                    pixel_y = (
                        char_y * 4
                        + local_y
                    )

                    if (
                        pixel_x < pixel_width
                        and pixel_y < pixel_height
                        and (
                            pixel_x,
                            pixel_y,
                        ) in pixels
                    ):
                        dots.add(
                            (
                                local_x,
                                local_y,
                            )
                        )

            if not dots:
                line += " "
                continue

            temperature_index = min(
                char_x * 2,
                len(values) - 1,
            )

            temperature = values[
                temperature_index
            ]

            color = _ansi_color(
                temperature,
                minimum=minimum,
                maximum=maximum,
            )

            line += (
                f"{color}"
                f"{_braille_char(dots)}"
                f"{_RESET}"
            )

        lines.append(line)

    return lines


def _format_axis_value(
    value: float,
) -> str:
    if value.is_integer():
        return str(int(value))

    return f"{value:.1f}"


def _render_time_axis(
    points: Sequence[WeatherPoint],
    *,
    char_width: int,
) -> str:
    if not points or char_width <= 0:
        return ""

    labels: list[
        tuple[int, str]
    ] = []

    for index, point in enumerate(points):
        if point.time.hour % 4 == 0:
            labels.append(
                (
                    index,
                    point.time.strftime("%H"),
                )
            )

    axis = [" "] * char_width

    for index, label in labels:
        position = round(
            index
            * (char_width - 1)
            / max(
                1,
                len(points) - 1,
            )
        )

        start = max(
            0,
            min(
                char_width - len(label),
                position
                - len(label) // 2,
            ),
        )

        for offset, character in enumerate(
            label
        ):
            target = start + offset

            if target < char_width:
                axis[target] = character

    return "".join(axis)


def _axis_labels_by_row(
    *,
    graph_height: int,
    pixel_height: int,
    minimum: float,
    maximum: float,
    step: float,
) -> dict[int, str]:
    labels: dict[int, str] = {}

    if graph_height <= 0:
        return labels

    current = maximum

    while (
        current
        >= minimum - step / 10
    ):
        normalized = (
            (current - minimum)
            / (maximum - minimum)
            if maximum > minimum
            else 0.5
        )

        pixel_y = round(
            (1.0 - normalized)
            * (pixel_height - 1)
        )

        row = min(
            graph_height - 1,
            pixel_y // 4,
        )

        labels[row] = (
            f"{_format_axis_value(current)}°"
        )

        current -= step

    return labels


def weather_symbol(
    weather_code: int | None,
) -> str:
    if weather_code is None:
        return "?"

    if weather_code == 0:
        return "☀"

    if weather_code in (1, 2):
        return "🌤"

    if weather_code == 3:
        return "☁"

    if weather_code in (45, 48):
        return "🌫"

    if weather_code in (
        51,
        53,
        55,
        56,
        57,
    ):
        return "🌦"

    if weather_code in (
        61,
        63,
        65,
        66,
        67,
    ):
        return "🌧"

    if weather_code in (
        71,
        73,
        75,
        77,
    ):
        return "🌨"

    if weather_code in (
        80,
        81,
        82,
    ):
        return "🌦"

    if weather_code in (
        95,
        96,
        99,
    ):
        return "⛈"

    return "?"


def weather_color(
    weather_code: int | None,
) -> tuple[int, int, int]:
    if weather_code == 0:
        return (255, 210, 40)

    if weather_code in (1, 2):
        return (255, 220, 80)

    if weather_code == 3:
        return (170, 180, 195)

    if weather_code in (45, 48):
        return (150, 160, 170)

    if weather_code in (
        51,
        53,
        55,
        56,
        57,
    ):
        return (90, 190, 255)

    if weather_code in (
        61,
        63,
        65,
        66,
        67,
    ):
        return (60, 150, 255)

    if weather_code in (
        71,
        73,
        75,
        77,
    ):
        return (150, 225, 255)

    if weather_code in (
        80,
        81,
        82,
    ):
        return (70, 175, 255)

    if weather_code in (
        95,
        96,
        99,
    ):
        return (190, 120, 255)

    return (180, 180, 180)


def _weather_ansi_color(
    weather_code: int | None,
) -> str:
    red, green, blue = weather_color(
        weather_code
    )

    return (
        f"\033[38;2;"
        f"{red};{green};{blue}m"
    )


def _render_weather_axis(
    points: Sequence[WeatherPoint],
    *,
    char_width: int,
) -> str:
    if not points or char_width <= 0:
        return ""

    axis = [" "] * char_width

    for index, point in enumerate(points):
        if point.time.hour % 4 != 0:
            continue

        position = round(
            index
            * (char_width - 1)
            / max(
                1,
                len(points) - 1,
            )
        )

        symbol = weather_symbol(
            point.weather_code
        )

        color = _weather_ansi_color(
            point.weather_code
        )

        colored_symbol = (
            f"{color}"
            f"{symbol}"
            f"{_RESET}"
        )

        if position < char_width:
            axis[position] = colored_symbol

    return "".join(axis)


def render_weather_strip(
    points: Sequence[WeatherPoint],
    *,
    width: int = 32,
) -> str:
    if not points:
        return "No weather data."

    weather_width = max(
        2,
        width,
    )

    weather_axis = _render_weather_axis(
        points,
        char_width=weather_width,
    )

    time_axis = _render_time_axis(
        points,
        char_width=weather_width,
    )

    return "\n".join(
        (
            weather_axis,
            time_axis,
        )
    )


def render_precipitation_chart(
    points: Sequence[WeatherPoint],
    *,
    width: int = 32,
    height: int = 6,
) -> str:
    if not points:
        return "No precipitation data."

    visible_points = [
        point
        for point in points
        if point.time.hour % 4 == 0
    ]

    if not visible_points:
        visible_points = list(points)

    chart_width = max(
        2,
        width,
    )

    probabilities = [
        point.precipitation_probability
        if point.precipitation_probability
        is not None
        else 0
        for point in visible_points
    ]

    no_rain = all(
        probability == 0
        for probability in probabilities
    )

    slot_width = max(
        1,
        chart_width
        // len(visible_points),
    )

    bar_width = max(
        1,
        min(
            3,
            slot_width - 1,
        ),
    )

    bar_levels = (
        100,
        80,
        60,
        40,
        20,
    )

    lines: list[str] = []

    for level in bar_levels:
        line = ""

        for point in visible_points:
            probability = (
                point.precipitation_probability
                if point.precipitation_probability
                is not None
                else 0
            )

            filled = (
                probability >= level
            )

            bar = (
                "█" * bar_width
                if filled
                else " " * bar_width
            )

            padding = (
                " "
                * (
                    slot_width
                    - bar_width
                )
            )

            line += bar + padding

        if no_rain and level == 40:
            message = "no rain today"

            message_start = max(
                0,
                (
                    chart_width
                    - len(message)
                )
                // 2,
            )

            line_chars = list(
                line[:chart_width]
            )

            for index, character in enumerate(
                message
            ):
                target = (
                    message_start
                    + index
                )

                if target < chart_width:
                    line_chars[target] = character

            line = "".join(line_chars)

        lines.append(
            line[:chart_width]
        )

    time_axis = _render_time_axis(
        visible_points,
        char_width=chart_width,
    )

    rendered: list[str] = []

    for level, line in zip(
        bar_levels,
        lines,
    ):
        rendered.append(
            f"{level:>3}% │ {line}"
        )

    rendered.append(
        f"{'0':>3}% └"
        + "─" * chart_width
    )

    rendered.append(
        "      " + time_axis
    )

    return "\n".join(rendered)


def wind_level(
    speed_kmh: float | None,
) -> str:
    if speed_kmh is None:
        return "Unknown"

    if speed_kmh < 10:
        return "Light"

    if speed_kmh < 25:
        return "Moderate"

    return "Strong"


def wind_symbol(
    speed_kmh: float | None,
) -> str:
    if speed_kmh is None:
        return "?"

    if speed_kmh < 10:
        return "🌬"

    return "💨"


def wind_color(
    speed_kmh: float | None,
) -> tuple[int, int, int]:
    if speed_kmh is None:
        return (150, 150, 150)

    if speed_kmh < 10:
        return (100, 210, 255)

    if speed_kmh < 25:
        return (255, 220, 70)

    return (255, 120, 60)


def _wind_ansi_color(
    speed_kmh: float | None,
) -> str:
    red, green, blue = wind_color(
        speed_kmh
    )

    return (
        f"\033[38;2;"
        f"{red};{green};{blue}m"
    )


def _wind_period(
    hour: int,
) -> str | None:
    if 6 <= hour <= 9:
        return "Morning"

    if 10 <= hour <= 12:
        return "Midday"

    if 13 <= hour <= 17:
        return "Afternoon"

    if 18 <= hour <= 23:
        return "Evening"

    return None


def render_wind_summary(
    points: Sequence[WeatherPoint],
) -> str:
    """
    Render a simple wind summary for four periods of the day.

    Morning:   06:00-09:59
    Midday:    10:00-12:59
    Afternoon: 13:00-17:59
    Evening:   18:00-23:59
    """
    periods = (
        "Morning",
        "Midday",
        "Afternoon",
        "Evening",
    )

    grouped: dict[
        str,
        list[float],
    ] = {
        period: []
        for period in periods
    }

    for point in points:
        period = _wind_period(
            point.time.hour
        )

        if (
            period is not None
            and point.wind_speed is not None
        ):
            grouped[period].append(
                point.wind_speed
            )

    rendered: list[str] = []

    for period in periods:
        speeds = grouped[period]

        if not speeds:
            rendered.append(
                f"  {period:<10} "
                f"⚪  No data"
            )
            continue

        # A napszakot a várható legerősebb
        # széllökés alapján kategorizáljuk.
        # Így egy rövid, de erős szeles időszak
        # sem tűnik el az átlagolásban.
        peak_speed = max(speeds)

        level = wind_level(
            peak_speed
        )

        symbol = wind_symbol(
            peak_speed
        )

        color = _wind_ansi_color(
            peak_speed
        )

        rendered.append(
            f"  {period:<10}"
            f"{color}{symbol}{_RESET}"
            f"  {color}{level:<9}{_RESET}"
            f"{peak_speed:>5.0f} km/h"
        )

    return "\n".join(rendered)


def render_temperature_chart(
    points: Sequence[WeatherPoint],
    *,
    width: int = 32,
    height: int = 10,
) -> str:
    if not points:
        return "No temperature data."

    temperatures = [
        point.temperature
        for point in points
    ]

    data_minimum = min(
        temperatures
    )

    data_maximum = max(
        temperatures
    )

    minimum, maximum, step = (
        _temperature_axis(
            data_minimum,
            data_maximum,
        )
    )

    pixel_width = max(
        2,
        width * 2,
    )

    pixel_height = max(
        4,
        height * 4,
    )

    values = _interpolate(
        temperatures,
        pixel_width,
    )

    pixels = _plot_line(
        values,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        minimum=minimum,
        maximum=maximum,
    )

    graph = _render_braille(
        pixels,
        values,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        minimum=minimum,
        maximum=maximum,
    )

    graph_height = len(graph)

    axis_labels = _axis_labels_by_row(
        graph_height=graph_height,
        pixel_height=pixel_height,
        minimum=minimum,
        maximum=maximum,
        step=step,
    )

    rendered: list[str] = []

    for row_index, line in enumerate(graph):
        label = axis_labels.get(
            row_index
        )

        if label is not None:
            rendered.append(
                f"{label:>5} ┤ {line}"
            )
        else:
            rendered.append(
                f"{'':>5} │ {line}"
            )

    graph_width = (
        pixel_width + 1
    ) // 2

    rendered.append(
        "     └"
        + "─" * (graph_width + 1)
    )

    time_axis = _render_time_axis(
        points,
        char_width=graph_width,
    )

    rendered.append(
        "      " + time_axis
    )

    return "\n".join(rendered)
