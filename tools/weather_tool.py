import requests

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

def get_weather(city: str) -> str:
    geo_url = "https://nominatim.openstreetmap.org/search"
    geo_params = {"q": city, "format": "json", "limit": 1}
    geo_resp = requests.get(geo_url, params=geo_params, headers={"User-Agent": "weather-agent"})
    geo_resp.raise_for_status()
    geo_data = geo_resp.json()
    if not geo_data:
        return f"City '{city}' not found"
    lat = float(geo_data[0]["lat"])
    lon = float(geo_data[0]["lon"])

    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {"latitude": lat, "longitude": lon, "current_weather": True}
    weather_resp = requests.get(weather_url, params=weather_params)
    weather_resp.raise_for_status()
    data = weather_resp.json()
    cw = data.get("current_weather")
    if not cw:
        return f"No weather data available for {city}"

    temperature = cw.get("temperature")
    windspeed = cw.get("windspeed")
    weathercode = cw.get("weathercode")
    weather_desc = WEATHER_CODES.get(weathercode, "Unknown")

    return f"Weather in {city}: {weather_desc}, Temperature {temperature}°C, Wind {windspeed} m/s"
