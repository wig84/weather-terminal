from collections.abc import Sequence

from .models import WeatherPoint


# Braille Unicode:
#
#   1 4
#   2 5
#   3 6
#   7 8
#
# Egy karakter tehát 2 x 4 "pixel".
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
    """Convert 2x4 pixel coordinates into one Braille character."""
    value = 0

    for x, y in pixels:
        value |= _BRAILLE_DOTS[(x, y)]

    return chr(0x2800 + value)


def _interpolate(
    values: Sequence[float],
    width: int,
) -> list[float]:
    """Resample values to the requested pixel width."""
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
    """Choose a human-friendly axis step."""
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
    """Create a temperature axis with 20% padding around the daily range."""
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
    """Create a pixel representation of a line."""
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
    """
    Map temperature to a
    blue -> cyan -> green -> yellow -> orange -> red gradient.
    """
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
    """Return an ANSI truecolor escape sequence."""
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
    """Convert the pixel grid into colored Braille characters."""
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
    """Format an axis value without unnecessary decimals."""
    if value.is_integer():
        return str(int(value))

    return f"{value:.1f}"


def _render_time_axis(
    points: Sequence[WeatherPoint],
    *,
    char_width: int,
) -> str:
    """Render a compact time axis aligned with the graph."""
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
    """Map temperature axis labels to the corresponding graph rows."""
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
    """Convert a WMO weather code into a terminal-friendly symbol."""
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

    if weather_code in (51, 53, 55, 56, 57):
        return "🌦"

    if weather_code in (61, 63, 65, 66, 67):
        return "🌧"

    if weather_code in (71, 73, 75, 77):
        return "🌨"

    if weather_code in (80, 81, 82):
        return "🌦"

    if weather_code in (95, 96, 99):
        return "⛈"

    return "?"


def weather_color(
    weather_code: int | None,
) -> tuple[int, int, int]:
    """Return an RGB color for a WMO weather code."""
    if weather_code == 0:
        return (255, 210, 40)

    if weather_code in (1, 2):
        return (255, 220, 80)

    if weather_code == 3:
        return (170, 180, 195)

    if weather_code in (45, 48):
        return (150, 160, 170)

    if weather_code in (51, 53, 55, 56, 57):
        return (90, 190, 255)

    if weather_code in (61, 63, 65, 66, 67):
        return (60, 150, 255)

    if weather_code in (71, 73, 75, 77):
        return (150, 225, 255)

    if weather_code in (80, 81, 82):
        return (70, 175, 255)

    if weather_code in (95, 96, 99):
        return (190, 120, 255)

    return (180, 180, 180)


def _weather_ansi_color(
    weather_code: int | None,
) -> str:
    """Return an ANSI truecolor sequence for a weather code."""
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
    """Render colored weather symbols aligned with the time axis."""
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
    """Render colored weather symbols with a compact time axis."""
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
    """Render precipitation probability as a compact bar chart."""
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

    chart_height = max(
        1,
        height,
    )

    probabilities = [
        point.precipitation_probability
        if point.precipitation_probability
        is not None
        else 0
        for point in visible_points
    ]

    # Ha egész nap 0% a csapadékvalószínűség,
    # ne üres diagramot jelenítsünk meg.
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

    # Öt oszlopsor: 100, 80, 60, 40, 20%.
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

    # A 0%-os baseline.
    lines.append(
        "─" * chart_width
    )

    time_axis = _render_time_axis(
        visible_points,
        char_width=chart_width,
    )

    lines.append(time_axis)

    rendered: list[str] = []

    for level, line in zip(
        bar_levels,
        lines[:len(bar_levels)],
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


def render_temperature_chart(
    points: Sequence[WeatherPoint],
    *,
    width: int = 32,
    height: int = 10,
) -> str:
    """Render a colored temperature chart using Braille characters."""
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
