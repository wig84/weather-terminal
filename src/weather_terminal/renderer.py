from collections.abc import Sequence

from .models import WeatherPoint


def render_temperature_chart(
    points: Sequence[WeatherPoint],
    *,
    width: int = 40,
    height: int = 8,
) -> str:
    """Render a temperature chart using Unicode characters."""

    if not points:
        return "No temperature data."

    temperatures = [point.temperature for point in points]

    # A grafikon vízszintes felbontása nem lehet nagyobb,
    # mint ahány adatpontunk van.
    chart_width = min(width, len(temperatures))

    # Ha több adatpont van, mint amennyit meg akarunk jeleníteni,
    # egyenletesen mintavételezünk.
    if len(temperatures) > chart_width:
        indices = [
            round(i * (len(temperatures) - 1) / (chart_width - 1))
            for i in range(chart_width)
        ]
        values = [temperatures[i] for i in indices]
    else:
        values = temperatures

    minimum = min(values)
    maximum = max(values)

    # Legyen legalább egy kis függőleges tartomány akkor is,
    # ha minden hőmérséklet azonos.
    if maximum == minimum:
        minimum -= 1
        maximum += 1

    rows: list[str] = []

    for row in range(height):
        # Fentről lefelé haladunk.
        level = maximum - (maximum - minimum) * row / (height - 1)

        line = f"{level:4.0f}° ┤"

        for value in values:
            normalized = (value - minimum) / (maximum - minimum)
            value_row = round((1 - normalized) * (height - 1))

            if value_row == row:
                line += "●"
            else:
                line += " "

        rows.append(line)

    axis = "     └" + "─" * len(values)

    return "\n".join(rows + [axis])
