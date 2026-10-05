import sys
from datetime import datetime, timedelta

from weather_terminal import cli
from weather_terminal.models import WeatherForecast, WeatherPoint


def make_forecast() -> WeatherForecast:
    points = tuple(
        WeatherPoint(
            time=datetime(2026, 10, 2) + timedelta(hours=hour),
            temperature=20.0,
            precipitation_probability=0,
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


def patch_renderers(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "render_temperature_chart",
        lambda *args, **kwargs: "TEMPERATURE_CHART",
    )
    monkeypatch.setattr(
        cli,
        "render_weather_strip",
        lambda *args, **kwargs: "WEATHER_STRIP",
    )
    monkeypatch.setattr(
        cli,
        "render_precipitation_chart",
        lambda *args, **kwargs: "PRECIPITATION_CHART",
    )
    monkeypatch.setattr(
        cli,
        "render_wind_summary",
        lambda *args, **kwargs: "WIND_SUMMARY",
    )
    monkeypatch.setattr(
        cli,
        "fetch_forecast",
        lambda **kwargs: make_forecast(),
    )


def test_compact_option_removes_context(monkeypatch, capsys):
    patch_renderers(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["termweather", "--compact"],
    )

    cli.main()

    output = capsys.readouterr().out

    assert "Weather: Budapest" not in output
    assert "Timezone: Europe/Budapest" not in output
    assert "  WEATHER\n" not in output
    assert "  PRECIPITATION\n" not in output
    assert "Forecast:" not in output
    assert "  TEMPERATURE\n" not in output
    assert "  WIND\n" not in output
    assert "TEMPERATURE_CHART" in output
    assert "WEATHER_STRIP" in output
    assert "PRECIPITATION_CHART" in output
    assert "WIND_SUMMARY" in output
    assert "  HUMIDITY\n" not in output
    assert "Humidity: 45%" in output


def test_default_layout_keeps_context(monkeypatch, capsys):
    patch_renderers(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["termweather"],
    )

    cli.main()

    output = capsys.readouterr().out

    assert "Weather: Budapest" in output
    assert "Timezone: Europe/Budapest" in output
    assert "Forecast: 2026-10-02" in output
    assert "  TEMPERATURE\n" in output
    assert "  WIND\n" in output
    assert "TEMPERATURE_CHART" in output
    assert "WEATHER_STRIP" in output
    assert "PRECIPITATION_CHART" in output
    assert "WIND_SUMMARY" in output
    assert "  HUMIDITY\n" in output
    assert "  Humidity: 45%" in output


def test_select_forecast_points_returns_tomorrow():
    forecast = make_forecast()

    points = cli.select_forecast_points(
        forecast.points,
        tomorrow=True,
    )

    assert len(points) == 24
    assert points[0].time == datetime(2026, 10, 3, 0)
    assert points[-1].time == datetime(2026, 10, 3, 23)


def test_tomorrow_option_uses_tomorrows_forecast(monkeypatch, capsys):
    patch_renderers(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["termweather", "--tomorrow"],
    )

    cli.main()

    output = capsys.readouterr().out

    assert "Forecast: 2026-10-03" in output
    assert "Forecast: 2026-10-02" not in output


def test_tomorrow_option_works_with_compact(monkeypatch, capsys):
    patch_renderers(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["termweather", "--tomorrow", "--compact"],
    )

    cli.main()

    output = capsys.readouterr().out

    assert "Forecast:" not in output
    assert "TEMPERATURE_CHART" in output
    assert "WIND_SUMMARY" in output
