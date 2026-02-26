"""
Venlo Weer App - Streamlit weerapplicatie voor Venlo met Open-Meteo API
"""

import math
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd
import altair as alt
from datetime import datetime

# Venlo coördinaten (exact: stadhuis)
VENLO_LAT = 51.3700
VENLO_LON = 6.1681

# Buienradar radar-afbeelding (hele NL/BE)
RADAR_URL = "https://api.buienradar.nl/image/1.0/RadarMapNL?width=550&height=512"

st.set_page_config(
    page_title="Venlo Weer",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS voor betere styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .wind-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=600)  # Cache 10 minuten
def fetch_weather_data(lat: float, lon: float) -> dict | None:
    """Haal weerdata op van de Open-Meteo API."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_direction_10m_dominant",
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code",
        "timezone": "Europe/Amsterdam",
        "forecast_days": 7
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Fout bij ophalen weerdata: {e}")
        return None


def get_weather_emoji(code: int) -> str:
    """Converteer WMO weer code naar emoji."""
    codes = {
        0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
        51: "🌧️", 53: "🌧️", 55: "🌧️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
        66: "🌨️", 67: "🌨️", 71: "❄️", 73: "❄️", 75: "❄️",
        77: "❄️", 80: "🌦️", 81: "🌦️", 82: "🌦️", 85: "🌨️", 86: "🌨️",
        95: "⛈️", 96: "⛈️", 99: "⛈️"
    }
    return codes.get(code, "🌡️")


def direction_to_text(degrees: int) -> str:
    """Converteer windrichting in graden naar tekst."""
    directions = ["N", "NNO", "NO", "ONO", "O", "OZO", "ZO", "ZZO", "Z", "ZZW", "ZW", "WZW", "W", "WNW", "NW", "NNW"]
    idx = round(degrees / 22.5) % 16
    return directions[idx]


def main():
    st.markdown('<p class="main-header">🌤️ Venlo Weer App</p>', unsafe_allow_html=True)

    # Vernieuwknop
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        if st.button("🔄 Data vernieuwen", type="primary"):
            fetch_weather_data.clear()
            st.rerun()

    st.markdown("---")

    # Haal weerdata op
    with st.spinner("Weerdata ophalen..."):
        data = fetch_weather_data(VENLO_LAT, VENLO_LON)

    if not data:
        return

    # Ondersteun zowel "current" als "current_weather" (oude API)
    current = data.get("current") or data.get("current_weather", {})
    if "windspeed" in current and "wind_speed_10m" not in current:
        current["wind_speed_10m"] = current["windspeed"]
        current["wind_direction_10m"] = current.get("winddirection", 0)
        current["temperature_2m"] = current.get("temperature", 0)
        current["weather_code"] = current.get("weathercode", 0)
        current["relative_humidity_2m"] = None
    hourly = data.get("hourly", {})
    daily = data.get("daily", {})

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Instellingen")
        st.info(f"📍 **Locatie:** Venlo, Limburg")
        st.caption(f"Coördinaten: {VENLO_LAT}°N, {VENLO_LON}°E")
        st.markdown("---")
        st.subheader("🌡️ Nu")
        weather_code = current.get("weather_code", 0)
        st.markdown(f"**{get_weather_emoji(weather_code)}** Huidig weer")

    # --- Huidig weer ---
    st.subheader("📍 Huidig weer in Venlo")

    col1, col2, col3, col4, col5 = st.columns(5)

    temp = current.get("temperature_2m", 0)
    humidity = current.get("relative_humidity_2m") or 0
    wind_speed = current.get("wind_speed_10m", 0)
    wind_dir = current.get("wind_direction_10m", 0)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{temp:.1f}°C</div>
            <div class="metric-label">Temperatuur</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{humidity:.0f}%</div>
            <div class="metric-label">Luchtvochtigheid</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="wind-card">
            <div class="metric-value">{wind_speed:.1f} km/h</div>
            <div class="metric-label">Windsnelheid</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="wind-card">
            <div class="metric-value">{direction_to_text(wind_dir)}</div>
            <div class="metric-label">Windrichting ({wind_dir}°)</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{get_weather_emoji(weather_code)}</div>
            <div class="metric-label">Weertype</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Tabs: Uurlijks, Dagelijks, Kaart, Radar ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Uurlijks weer", "📅 7-dagen verwachting", "🗺️ Interactieve kaart", "🌧️ Radar"])

    with tab1:
        st.subheader("Uurlijkse verwachting (48 uur)")
        times = hourly.get("time", [])[:48]
        temps = hourly.get("temperature_2m", [])[:48]
        wind_speeds = hourly.get("wind_speed_10m", [])[:48]
        wind_dirs = hourly.get("wind_direction_10m", [])[:48]
        precip_probs = hourly.get("precipitation_probability", [None] * 48)[:48]

        df_hourly = pd.DataFrame({
            "Tijd": [t[11:16] if len(t) > 10 else t for t in times],
            "Datum": [t[:10] for t in times],
            "Temp (°C)": temps,
            "Wind (km/h)": wind_speeds,
            "Windrichting": [direction_to_text(d) for d in wind_dirs],
            "Neerslag %": precip_probs
        })

        st.dataframe(df_hourly, use_container_width=True, hide_index=True)

        # Lijn grafieken (oranje)
        chart_df = pd.DataFrame({
            "Tijd": [t[11:16] if len(t) > 10 else t for t in times],
            "Temperatuur (°C)": temps,
            "Windsnelheid (km/h)": wind_speeds
        })
        orange = "#ff8c00"
        chart_temp = alt.Chart(chart_df).mark_line(color=orange).encode(
            x=alt.X("Tijd:N", title="Tijd"),
            y=alt.Y("Temperatuur (°C):Q", title="Temperatuur (°C)")
        ).properties(height=180)
        chart_wind = alt.Chart(chart_df).mark_line(color=orange).encode(
            x=alt.X("Tijd:N", title="Tijd"),
            y=alt.Y("Windsnelheid (km/h):Q", title="Windsnelheid (km/h)")
        ).properties(height=180)
        st.altair_chart(alt.vconcat(chart_temp, chart_wind), use_container_width=True)

    with tab2:
        st.subheader("7-dagen verwachting")
        daily_times = daily.get("time", [])
        daily_max = daily.get("temperature_2m_max", [])
        daily_min = daily.get("temperature_2m_min", [])
        daily_precip = daily.get("precipitation_sum", [])
        daily_wind_max = daily.get("wind_speed_10m_max", [])
        daily_wind_dir = daily.get("wind_direction_10m_dominant", [])

        df_daily = pd.DataFrame({
            "Datum": daily_times,
            "Max (°C)": daily_max,
            "Min (°C)": daily_min,
            "Neerslag (mm)": daily_precip,
            "Max wind (km/h)": daily_wind_max,
            "Windrichting": [direction_to_text(d) for d in daily_wind_dir]
        })

        st.dataframe(df_daily, use_container_width=True, hide_index=True)

        orange = "#ff8c00"
        col_a, col_b = st.columns(2)
        with col_a:
            df_temp = df_daily.melt(id_vars=["Datum"], value_vars=["Max (°C)", "Min (°C)"], var_name="Type", value_name="°C")
            bar_temp = alt.Chart(df_temp).mark_bar().encode(
                x=alt.X("Datum:N", title="Datum"),
                y=alt.Y("°C:Q", title="Temperatuur (°C)"),
                color=alt.Color("Type:N", scale=alt.Scale(range=[orange, "#ffa500"]))
            ).properties(height=250)
            st.altair_chart(bar_temp, use_container_width=True)
        with col_b:
            if daily_wind_max:
                st.altair_chart(alt.Chart(df_daily).mark_bar(color=orange).encode(
                    x=alt.X("Datum:N", title="Datum"),
                    y=alt.Y("Max wind (km/h):Q", title="Max wind (km/h)")
                ).properties(height=250), use_container_width=True)
            else:
                st.info("Windgegevens niet beschikbaar voor dagelijkse data")

    with tab3:
        st.subheader("Interactieve kaart - Venlo")
        m = folium.Map(
            location=[VENLO_LAT, VENLO_LON],
            zoom_start=13,
            tiles="OpenStreetMap"
        )

        # Popup met weerinfo
        popup_html = f"""
        <div style="font-family: Arial; min-width: 180px;">
            <h4 style="margin: 0 0 10px 0;">🌤️ Venlo</h4>
            <p style="margin: 5px 0;"><b>Temperatuur:</b> {temp:.1f}°C</p>
            <p style="margin: 5px 0;"><b>Wind:</b> {wind_speed:.1f} km/h {direction_to_text(wind_dir)}</p>
            <p style="margin: 5px 0;"><b>Luchtvochtigheid:</b> {humidity:.0f}%</p>
        </div>
        """
        folium.Marker(
            [VENLO_LAT, VENLO_LON],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip="Venlo - klik voor weerinfo",
            icon=folium.Icon(color="blue", icon="cloud")
        ).add_to(m)

        # Windrichting als pijl op de kaart (indicatief)
        arrow_len = 0.02
        rad = math.radians(270 - wind_dir)  # North = 0
        end_lat = VENLO_LAT + arrow_len * math.cos(rad)
        end_lon = VENLO_LON + arrow_len * math.sin(rad)
        folium.PolyLine(
            [[VENLO_LAT, VENLO_LON], [end_lat, end_lon]],
            color="blue",
            weight=3
        ).add_to(m)

        st_folium(m, use_container_width=True, returned_objects=[])

        # Tabel met exacte coördinaten
        st.subheader("📍 Coördinaten Venlo")
        df_coords = pd.DataFrame({
            "Eigenschap": ["Breedtegraad (Noord)", "Lengtegraad (Oost)", "Decimaal", "DMS"],
            "Waarde": [
                f"{VENLO_LAT}° N",
                f"{VENLO_LON}° E",
                f"{VENLO_LAT:.4f}, {VENLO_LON:.4f}",
                "51°22'12\" N, 6°10'5\" E"
            ]
        })
        st.dataframe(df_coords, use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("🌧️ Neerslagradar (Nederland)")
        st.caption("Bron: Buienradar (radar overzicht Nederland/België)")
        st.image(
            RADAR_URL,
            caption="Actuele radar (Buienradar)",
            use_column_width=True,
        )

    st.markdown("---")
    st.caption("Data via [Open-Meteo.com](https://open-meteo.com/) • Laatste update: " + datetime.now().strftime("%d-%m-%Y %H:%M"))


if __name__ == "__main__":
    main()
