from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from weather_terminal import web
from weather_terminal.models import WeatherForecast, WeatherPoint


def make_forecast() -> WeatherForecast:
    points = tuple(
        WeatherPoint(
            time=datetime(2026, 10, 2) + timedelta(hours=hour),
            temperature=20.0 + hour / 10,
            precipitation_probability=hour % 100,
            weather_code=0,
            wind_speed=5.0,
            humidity=45,
        )
        for hour in range(48)
    )
    return WeatherForecast(
        location="Budapest",
        latitude=47.4979,
        longitude=19.0402,
        timezone="Europe/Budapest",
        points=points,
    )


def test_health_endpoint():
    client = TestClient(web.app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_forecast_defaults_to_today(monkeypatch):
    monkeypatch.setattr(web, "fetch_forecast", lambda **kwargs: make_forecast())
    client = TestClient(web.app)

    response = client.get("/api/forecast")

    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Budapest"
    assert data["timezone"] == "Europe/Budapest"
    assert data["day"] == "today"
    assert data["date"] == "2026-10-02"
    assert len(data["points"]) == 24
    assert data["points"][0]["time"] == "2026-10-02T00:00:00"
    assert data["points"][0]["humidity"] == 45


def test_forecast_returns_tomorrow(monkeypatch):
    monkeypatch.setattr(web, "fetch_forecast", lambda **kwargs: make_forecast())
    client = TestClient(web.app)

    response = client.get("/api/forecast?day=tomorrow")

    assert response.status_code == 200
    data = response.json()
    assert data["day"] == "tomorrow"
    assert data["date"] == "2026-10-03"
    assert len(data["points"]) == 24
    assert data["points"][0]["time"] == "2026-10-03T00:00:00"
    assert data["points"][-1]["time"] == "2026-10-03T23:00:00"


def test_forecast_rejects_unknown_day():
    client = TestClient(web.app)

    response = client.get("/api/forecast?day=next-week")

    assert response.status_code == 422


def test_forecast_handles_empty_provider_result(monkeypatch):
    forecast = make_forecast()
    empty_forecast = WeatherForecast(
        location=forecast.location,
        latitude=forecast.latitude,
        longitude=forecast.longitude,
        timezone=forecast.timezone,
        points=(),
    )
    monkeypatch.setattr(
        web,
        "fetch_forecast",
        lambda **kwargs: empty_forecast,
    )
    client = TestClient(web.app)

    response = client.get("/api/forecast")

    assert response.status_code == 502
    assert "no forecast points" in response.json()["detail"]
