from datetime import datetime

from weather_terminal.models import WeatherForecast, WeatherPoint


def test_weather_forecast_contains_points() -> None:
    point = WeatherPoint(
        time=datetime(2026, 10, 2, 10),
        temperature=17.5,
        precipitation_probability=20,
        weather_code=1,
    )

    forecast = WeatherForecast(
        location="Budapest",
        latitude=47.4979,
        longitude=19.0402,
        timezone="Europe/Budapest",
        points=(point,),
    )

    assert forecast.location == "Budapest"
    assert forecast.points[0].temperature == 17.5
