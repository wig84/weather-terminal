from datetime import datetime

import httpx

from .models import WeatherForecast, WeatherPoint

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_forecast(
    *,
    latitude: float,
    longitude: float,
    location: str = "Unknown",
) -> WeatherForecast:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,"
            "precipitation_probability,"
            "weather_code,"
            "wind_speed_10m,"
            "relative_humidity_2m"
        ),
        "forecast_days": 2,
        "timezone": "auto",
    }

    response = httpx.get(
        FORECAST_URL,
        params=params,
        timeout=10.0,
    )

    response.raise_for_status()

    data = response.json()

    hourly = data["hourly"]

    points = tuple(
        WeatherPoint(
            time=datetime.fromisoformat(time),
            temperature=temperature,
            precipitation_probability=precipitation,
            weather_code=code,
            wind_speed=wind_speed,
            humidity=humidity,
        )
        for time, temperature, precipitation, code, wind_speed, humidity in zip(
            hourly["time"],
            hourly["temperature_2m"],
            hourly["precipitation_probability"],
            hourly["weather_code"],
            hourly["wind_speed_10m"],
            hourly["relative_humidity_2m"],
        )
    )

    return WeatherForecast(
        location=location,
        latitude=data["latitude"],
        longitude=data["longitude"],
        timezone=data["timezone"],
        points=points,
    )
