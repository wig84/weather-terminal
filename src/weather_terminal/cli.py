import argparse

from .api import fetch_forecast
from .renderer import (
    render_precipitation_chart,
    render_temperature_chart,
    render_weather_strip,
    render_wind_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Terminal weather forecast"
    )

    parser.add_argument(
        "-c",
        "--compact",
        action="store_true",
        help="Show a space-saving forecast layout",
    )

    parser.add_argument(
        "--latitude",
        type=float,
        default=47.4979,
    )

    parser.add_argument(
        "--longitude",
        type=float,
        default=19.0402,
    )

    parser.add_argument(
        "--location",
        default="Budapest",
    )

    args = parser.parse_args()

    forecast = fetch_forecast(
        latitude=args.latitude,
        longitude=args.longitude,
        location=args.location,
    )

    points = forecast.points[:24]

    if not args.compact:
        print()
        print(
            f"  Weather: {forecast.location}"
        )

        print(
            f"  Timezone: {forecast.timezone}"
        )

        print()

    if not args.compact:
        print("  TEMPERATURE")
        print()

    print(
        render_temperature_chart(
            points,
            width=32,
            height=10,
        )
    )

    print()

    print(
        render_weather_strip(
            points,
            width=32,
        )
    )

    print()

    print(
        render_precipitation_chart(
            points,
            width=32,
            height=6,
        )
    )

    print()

    if not args.compact:
        print("  HUMIDITY")
        print()

    print(
        f"  Humidity: {points[0].humidity}%"
    )

    print()

    if not args.compact:
        print("  WIND")
        print()

    print(
        render_wind_summary(
            points
        )
    )

    if not args.compact:
        print()
        print(
            f"  Forecast: "
            f"{points[0].time:%Y-%m-%d}"
        )

    print()


if __name__ == "__main__":
    main()
