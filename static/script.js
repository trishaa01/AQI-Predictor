let chartInstance = null;

function renderChart(labels, data, title, color) {
  let ctx = document.getElementById("aqiChart");
  if (chartInstance) chartInstance.destroy();
  document.getElementById("chartTitle").innerHTML = title;
  chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: title,
        data: data,
        borderColor: color || "#4a90e2",
        backgroundColor: (color || "#4a90e2") + "22",
        borderWidth: 3,
        pointRadius: 5,
        fill: true,
        tension: 0.3,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: { y: { beginAtZero: false } }
    }
  });
}

async function getAQI() {
  let city = document.getElementById("city").value.trim();
  if (!city) { alert("Please enter a city name"); return; }

  document.getElementById("aqiValue").innerHTML    = "...";
  document.getElementById("aqiCategory").innerHTML = "Loading...";

  let res  = await fetch(`/get_aqi?city=${city}`);
  let data = await res.json();
  if (data.error) { alert(data.error); return; }

  document.getElementById("aqiValue").innerHTML    = data.aqi;
  document.getElementById("aqiCategory").innerHTML = data.category;
  document.getElementById("danger").innerHTML      = data.danger;
  document.getElementById("pm25").innerHTML        = data.pm25;
  document.getElementById("pm10").innerHTML        = data.pm10;
  document.getElementById("no2").innerHTML         = data.no2;
  document.getElementById("o3").innerHTML          = data.o3;

  document.querySelector(".aqi-card").className = "aqi-card " + getAqiClass(data.aqi);

  renderChart(
    ["PM2.5", "PM10", "NO2", "O3"],
    [data.pm25, data.pm10, data.no2, data.o3],
    "Current Pollution Levels", "#4a90e2"
  );
}

async function predictAQI() {
  let city = document.getElementById("city").value.trim();
  if (!city) { alert("Please enter a city name first"); return; }

  document.getElementById("predValue").innerHTML    = "⏳";
  document.getElementById("predCategory").innerHTML = "Fetching data...";
  document.getElementById("predSection").style.display = "block";

  let res  = await fetch(`/predict_aqi?city=${city}`);
  let data = await res.json();

  if (data.error) {
    document.getElementById("predCategory").innerHTML = "❌ " + data.error;
    document.getElementById("predValue").innerHTML    = "--";
    return;
  }

  document.getElementById("predValue").innerHTML    = data.predicted_aqi;
  document.getElementById("predCategory").innerHTML = data.category;
  document.getElementById("predDanger").innerHTML   = data.danger;
  document.getElementById("r2Score").innerHTML      = data.r2_score;
  document.getElementById("accPct").innerHTML       = data.accuracy_pct + "%";
  document.getElementById("mae").innerHTML          = data.mae + " AQI units";

  document.querySelector(".pred-card").className = "pred-card " + getAqiClass(data.predicted_aqi);

  let labels = data.trend.map(t => t.day);
  let values = data.trend.map(t => t.aqi);
  renderChart(labels, values, "AQI Trend + Tomorrow's Prediction", "#8e44ad");
}

function getAqiClass(aqi) {
  if (aqi <= 50)  return "good";
  if (aqi <= 100) return "moderate";
  if (aqi <= 150) return "sensitive";
  if (aqi <= 200) return "unhealthy";
  if (aqi <= 300) return "very-unhealthy";
  return "hazardous";
}
