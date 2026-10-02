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


def _braille_char(pixels: set[tuple[int, int]]) -> str:
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
        right = min(left + 1, len(values) - 1)

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

    # Add 20% of the actual daily temperature range
    # below the minimum and above the maximum.
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
    """Create a pixel representation of a temperature line."""
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
        hour = point.time.hour

        if hour % 4 == 0:
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

    # Egy Braille karakter 2 x 4 pixelt jelent.
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

    scale_values = []

    current = maximum

    while (
        current
        >= minimum - step / 10
    ):
        scale_values.append(current)
        current -= step

    rendered: list[str] = []

    for row, line in zip(
        scale_values,
        graph,
    ):
        label = _format_axis_value(row)

        rendered.append(
            f"{label:>4}° ┤ {line}"
        )

    # ANSI escape sequence-ek miatt a
    # len(graph[0]) nem használható.
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
