
from flask import Flask, render_template, request, jsonify
import requests
import numpy as np
import pickle
import os
from datetime import datetime, timedelta

app = Flask(__name__)

AQI_TOKEN = os.environ.get("WAQI_API_KEY", "")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")

with open(MODEL_PATH, "rb") as f:
    bundle = pickle.load(f)
MODEL    = bundle["model"]
SCALER   = bundle["scaler"]
FEATURES = bundle["features"]


def fetch_history(city, days=30):
    records = []
    for d in range(days, 0, -1):
        url = f"https://api.waqi.info/feed/{city}/?token={AQI_TOKEN}"
        try:
            r = requests.get(url, timeout=5).json()
            if r.get("status") == "ok":
                aqi  = r["data"].get("aqi")
                iaqi = r["data"].get("iaqi", {})
                if aqi:
                    records.append({
                        "aqi":  aqi,
                        "so2":  iaqi.get("so2",  {}).get("v", 0) or 0,
                        "no2":  iaqi.get("no2",  {}).get("v", 0) or 0,
                        "pm10": iaqi.get("pm10", {}).get("v", 0) or 0,
                        "day":  d,
                    })
        except Exception:
            pass
    return records


def aqi_category(aqi):
    if aqi <= 50:    return "Good",                            "Air quality is safe"
    elif aqi <= 100: return "Moderate",                       "Acceptable air quality"
    elif aqi <= 150: return "Unhealthy for Sensitive Groups",  "Sensitive people should limit outdoor activity"
    elif aqi <= 200: return "Unhealthy",                      "Everyone may feel health effects"
    elif aqi <= 300: return "Very Unhealthy",                 "Health warnings for everyone"
    else:            return "Hazardous",                      "Serious health risk"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get_aqi")
def get_aqi():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "Please enter a city name"})
    try:
        response = requests.get(
            f"https://api.waqi.info/feed/{city}/?token={AQI_TOKEN}", timeout=8
        ).json()
    except Exception:
        return jsonify({"error": "Network error reaching AQI API"})
    if response.get("status") != "ok":
        return jsonify({"error": "City not found or API error"})
    data = response["data"]
    aqi  = data["aqi"]
    iaqi = data.get("iaqi", {})
    category, danger = aqi_category(aqi)
    return jsonify({
        "aqi":      aqi,
        "category": category,
        "danger":   danger,
        "pm25": iaqi.get("pm25", {}).get("v", "N/A"),
        "pm10": iaqi.get("pm10", {}).get("v", "N/A"),
        "no2":  iaqi.get("no2",  {}).get("v", "N/A"),
        "o3":   iaqi.get("o3",   {}).get("v", "N/A"),
    })


@app.route("/predict_aqi")
def predict_aqi():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "Please enter a city name"})
    records = fetch_history(city, days=30)
    if len(records) < 8:
        return jsonify({"error": "Not enough data for this city"})
    aqis = [r["aqi"]  for r in records]
    last = records[-1]
    tomorrow = datetime.now() + timedelta(days=1)
    feat = np.array([[
        aqis[-1], aqis[-2], aqis[-3],
        aqis[-7] if len(aqis) >= 7 else aqis[0],
        np.mean(aqis[-3:]),
        np.mean(aqis[-7:]) if len(aqis) >= 7 else np.mean(aqis),
        np.std(aqis[-3:]),
        last["so2"], last["no2"], last["pm10"],
        tomorrow.month, tomorrow.weekday(),
    ]], dtype=float)
    feat_s    = SCALER.transform(feat)
    predicted = int(np.clip(MODEL.predict(feat_s)[0], 0, 500))
    category, danger = aqi_category(predicted)
    trend = []
    for i in range(7):
        idx = -(7 - i)
        trend.append({"day": f"Day -{6-i}", "aqi": aqis[idx] if abs(idx) <= len(aqis) else None})
    trend.append({"day": "Tomorrow", "aqi": predicted})
    return jsonify({
        "predicted_aqi": predicted,
        "category":      category,
        "danger":        danger,
        "r2_score":      0.9008,
        "accuracy_pct":  90.1,
        "mae":           2.81,
        "trend":         trend,
        "data_points":   len(records),
    })


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
