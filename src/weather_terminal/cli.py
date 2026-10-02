import argparse

from .api import fetch_forecast


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Terminal weather forecast"
    )
    parser.add_argument("--latitude", type=float, default=47.4979)
    parser.add_argument("--longitude", type=float, default=19.0402)
    parser.add_argument("--location", default="Budapest")

    args = parser.parse_args()

    forecast = fetch_forecast(
        latitude=args.latitude,
        longitude=args.longitude,
        location=args.location,
    )

    print(f"Weather: {forecast.location}")
    print(f"Timezone: {forecast.timezone}")
    print(f"Forecast points: {len(forecast.points)}")
    print()

    for point in forecast.points[:12]:
        rain = (
            f"{point.precipitation_probability}%"
            if point.precipitation_probability is not None
            else "-"
        )

        print(
            f"{point.time:%H:%M}  "
            f"{point.temperature:5.1f} °C  "
            f"rain {rain:>3}  "
            f"code {point.weather_code}"
        )


if __name__ == "__main__":
    main()
