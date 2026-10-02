# weather-terminal

Terminal weather forecast application with a graphical, space-efficient terminal presentation.

The project retrieves forecast data from Open-Meteo and renders temperature, weather conditions, precipitation probability, and wind information directly in the terminal.

## Welcome

**Project:** weather-terminal

**Description:** Terminal weather forecast application that displays temperature, weather conditions, precipitation probability, and wind information in a graphical terminal layout.

**Commands:**

```bash
termweather
termweather --compact
termweather --latitude 47.4979 --longitude 19.0402 --location Budapest
```

## Usage

### Default forecast

```bash
termweather
```

### Compact layout

```bash
termweather --compact
```

### Custom location

```bash
termweather --latitude 47.4979 --longitude 19.0402 --location Budapest
```

## Development

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project with development dependencies:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest -q
```
