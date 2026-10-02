from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WeatherPoint:
    time: datetime
    temperature: float
    precipitation_probability: int | None
    weather_code: int | None


@dataclass(frozen=True)
class WeatherForecast:
    location: str
    latitude: float
    longitude: float
    timezone: str
    points: tuple[WeatherPoint, ...]
