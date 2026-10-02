from datetime import datetime

import httpx

from .models import WeatherForecast, WeatherPoint

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_forecast(
    *, latitude: float, longitude: float, location: str = "Unknown"
) -> WeatherForecast:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": 2,
        "timezone": "auto",
    }

    response = httpx.get(FORECAST_URL, params=params, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    hourly = data["hourly"]

    points = tuple(
        WeatherPoint(
            time=datetime.fromisoformat(time),
            temperature=temperature,
            precipitation_probability=precipitation,
            weather_code=code,
        )
        for time, temperature, precipitation, code in zip(
            hourly["time"],
            hourly["temperature_2m"],
            hourly["precipitation_probability"],
            hourly["weather_code"],
        )
    )

    return WeatherForecast(
        location=location,
        latitude=data["latitude"],
        longitude=data["longitude"],
        timezone=data["timezone"],
        points=points,
    )
