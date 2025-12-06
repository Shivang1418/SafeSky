import requests
import random
import json
from django.shortcuts import render
from datetime import datetime
import pytz

API_KEY = '746bcd57c0faa0f89f1fd86f39dd7482'
CITIES = ["London", "New York", "Tokyo", "Paris", "Delhi", "Sydney", "Moscow"]


def get_wind_direction(degree):
    """Convert wind degree to direction name"""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    index = round(degree / 22.5) % 16
    return directions[index]


def home(request):
    city = request.GET.get('city')
    if not city:
        city = random.choice(CITIES)

    weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    try:
        response = requests.get(weather_url)
        data = response.json()

        if data.get('cod') != 200:
            weather_data = {'error': 'City not found.'}
            forecast_data = None
            aqi_data = None
        else:
            lat = data['coord']['lat']
            lon = data['coord']['lon']

            # --- Current weather ---
            weather_data = {
                'city': data['name'],
                'temperature': round(data['main']['temp'], 1),
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'wind_deg': data['wind']['deg'],
                'wind_direction': get_wind_direction(data['wind']['deg']),
            }

            # --- Forecast (every 2 hours) ---
            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
            forecast_response = requests.get(forecast_url)
            forecast_json = forecast_response.json()

            current_time = datetime.utcnow()
            all_forecasts = forecast_json['list']
            forecast_data = []

            for i in range(0, len(all_forecasts) - 1):
                curr = all_forecasts[i]
                next_ = all_forecasts[i + 1]

                forecast_time = datetime.strptime(curr['dt_txt'], '%Y-%m-%d %H:%M:%S')
                if forecast_time >= current_time:
                    forecast_data.append({
                        'time': curr['dt_txt'].split()[1][:5],
                        'temp': round(curr['main']['temp'], 1),
                        'humidity': curr['main']['humidity'],
                        'rain': curr.get('rain', {}).get('3h', 0),
                        'desc': curr['weather'][0]['description'].title(),
                        'icon': curr['weather'][0]['icon'],
                    })

                    if len(forecast_data) < 16:
                        avg_temp = round((curr['main']['temp'] + next_['main']['temp']) / 2, 1)
                        avg_humidity = round((curr['main']['humidity'] + next_['main']['humidity']) / 2, 1)
                        avg_rain = round((curr.get('rain', {}).get('3h', 0) + next_.get('rain', {}).get('3h', 0)) / 2, 2)

                        forecast_data.append({
                            'time': f"~{curr['dt_txt'].split()[1][:5]}+2h",
                            'temp': avg_temp,
                            'humidity': avg_humidity,
                            'rain': avg_rain,
                            'desc': curr['weather'][0]['description'].title(),
                            'icon': curr['weather'][0]['icon'],
                        })

                if len(forecast_data) >= 16:
                    break

            # --- Air Quality ---
            aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
            aqi_response = requests.get(aqi_url)
            aqi_json = aqi_response.json()
            aqi_index = aqi_json['list'][0]['main']['aqi']
            aqi_mapping = {
                1: "Good",
                2: "Fair",
                3: "Moderate",
                4: "Poor",
                5: "Very Poor"
            }
            aqi_data = aqi_mapping.get(aqi_index, "Unknown")

            # --- Graph Data ---
            times = [item['time'] for item in forecast_data]
            temps = [item['temp'] for item in forecast_data]
            humidity = [item['humidity'] for item in forecast_data]
            rain = [item['rain'] for item in forecast_data]

    except Exception as e:
        print("Error:", e)
        weather_data = {'error': 'Could not retrieve data.'}
        forecast_data = None
        aqi_data = None
        times, temps, humidity, rain = [], [], [], []

    context = {
        'weather': weather_data,
        'forecast': forecast_data,
        'aqi': aqi_data,
        'times_json': json.dumps(times),
        'temps_json': json.dumps(temps),
        'humidity_json': json.dumps(humidity),
        'rain_json': json.dumps(rain),
    }

    return render(request, 'weather/index.html', context)
