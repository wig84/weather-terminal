"""HTTP API for the weather-terminal forecast."""

from datetime import timedelta
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from .api import fetch_forecast

app = FastAPI(
    title="Termweather API",
    description="Hourly weather forecasts for the configured location.",
    version="0.1.0",
)

_UI_FILE = Path(__file__).parent / "static" / "index.html"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def weather_ui() -> HTMLResponse:
    """Serve the three-layout mobile weather interface."""
    return HTMLResponse(_UI_FILE.read_text(encoding="utf-8"))


@app.get("/api/health")
def health() -> dict[str, str]:
    """Simple health check that does not call the weather provider."""
    return {"status": "ok"}


@app.get("/api/forecast")
def get_forecast(
    day: Literal["today", "tomorrow"] = Query(
        default="today",
        description="Which calendar day's forecast to return.",
    ),
) -> dict:
    """Return hourly forecast data as JSON."""
    forecast = fetch_forecast(
        latitude=47.4979,
        longitude=19.0402,
        location="Budapest",
    )

    if not forecast.points:
        raise HTTPException(
            status_code=502,
            detail="The weather provider returned no forecast points.",
        )

    target_date = forecast.points[0].time.date()
    if day == "tomorrow":
        target_date += timedelta(days=1)

    points = tuple(
        point
        for point in forecast.points
        if point.time.date() == target_date
    )[:24]

    if not points:
        raise HTTPException(
            status_code=502,
            detail=f"No forecast data available for {day}.",
        )

    return {
        "location": forecast.location,
        "latitude": forecast.latitude,
        "longitude": forecast.longitude,
        "timezone": forecast.timezone,
        "day": day,
        "date": target_date.isoformat(),
        "points": [
            {
                "time": point.time.isoformat(),
                "temperature": point.temperature,
                "precipitation_probability": point.precipitation_probability,
                "weather_code": point.weather_code,
                "wind_speed": point.wind_speed,
                "humidity": point.humidity,
            }
            for point in points
        ],
    }
