import streamlit as st
import ttn
import json
import pandas as pd
from datetime import timedelta, datetime
import os
from dotenv import load_dotenv
from google.cloud import bigquery
from streamlit_folium import st_folium
import folium
from folium.plugins import HeatMap
import openmeteo_requests
import plotly.graph_objects as go
from geopy.distance import geodesic

load_dotenv()

st.set_page_config(
    page_title="Easy Tracker | by Severin",
    page_icon="👋",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://severin.io",
        "Report a bug": "https://severin.io",
        "About": "Boat Dashboard, Created by Severin Lindenmann",
    },
)

st.title("⛵ Easy | Boat Monitor")

AUTH_KEY = os.getenv("AUTH_KEY")
TTN_KEY = os.getenv("TTN_KEY")
PROJECT = os.getenv("PROJECT")
CLOUD = os.getenv("CLOUD")


@st.cache_resource
def create_bigquery_connection(PROJECT):
    if CLOUD == "TRUE":
        return bigquery.Client(PROJECT)
    else:
        from google.oauth2 import service_account

        GOOGLE_KEY_JSON = os.getenv("GOOGLE_KEY_JSON")
        GOOGLE_KEY_JSON = json.loads(GOOGLE_KEY_JSON)

        credentials = service_account.Credentials.from_service_account_info(
            GOOGLE_KEY_JSON
        )
        return bigquery.Client(credentials=credentials, project=PROJECT)


@st.cache_data
def query_bigquery_return_df(query, PROJECT):
    query_job = create_bigquery_connection(PROJECT).query(query)
    results = query_job.result()
    return results.to_dataframe()


# Function to check the key validity
def check_key(key):
    return key == AUTH_KEY


# Function to handle the authentication process
def handle_authentication():
    # Check if the key is already saved and valid
    if "auth_key" in st.session_state and check_key(st.session_state["auth_key"]):
        return True  # Authentication already succeeded in a previous step

    # Get the query parameters as a dictionary
    params = st.query_params.to_dict()
    url_key = params.get("auth")

    # If the key is provided in the URL and is correct, save it to session state and return True
    if url_key and check_key(url_key):
        st.session_state["auth_key"] = url_key  # Save the valid key in session state
        return True

    # If the key is incorrect or not provided, and there's no valid key in the session, prompt the user for the key
    key = st.text_input("Authentifizierungsschlüssel", value="")

    if key:  # Check if something is entered
        submit = st.button("Speichern")
        if submit and check_key(key):
            st.session_state["auth_key"] = key  # Save the valid key in session state
            st.rerun()  # Rerun the app to update the authentication status
            return True
        elif submit:
            st.error("Authentifizierung fehlgeschlagen. Bitte versuchen Sie es erneut.")

    # In case no key was provided in the URL and there's no interaction yet, display an initial prompt
    if not url_key and "auth_key" not in st.session_state:
        st.error(
            "Kein gültiger Authentifizierungsschlüssel gefunden. Bitte geben Sie den Schlüssel ein, ansonsten können Sie die Seite nicht nutzen."
        )

    return False  # Return False if authentication failed or hasn't been attempted


def history_data(today, before):
    query = f"""
SELECT * FROM `seli-data-storage.data_storage_1.sailing_boat` 
WHERE TIMESTAMP_TRUNC(received_at, DAY) BETWEEN TIMESTAMP("{before}") AND TIMESTAMP("{today}")
ORDER BY received_at DESC
    """
    df = query_bigquery_return_df(query, PROJECT)

    return df


def utc_to_cest_readable(utc_time):
    cest_time = utc_time + timedelta(hours=2)
    return cest_time.strftime("%d.%m.%Y %H:%M Uhr CEST")


def utc_to_cest(df):
    df["received_at"] = pd.to_datetime(df["received_at"])
    df["received_at"] = df["received_at"] + timedelta(hours=2)
    return df


@st.cache_resource
def get_openmeteo_client():
    return openmeteo_requests.Client()


@st.cache_data
def fetch_weather_data(past_days):
    # Initialize the Open-Meteo API client
    openmeteo = get_openmeteo_client()

    # Define the API request parameters
    params = {
        "latitude": 47.5659,
        "longitude": 9.3787,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
        ],
        "timezone": "Europe/Berlin",
        "past_days": past_days,
        "forecast_days": 1,
    }

    # Fetch weather data from the Open-Meteo API
    responses = openmeteo.weather_api(
        "https://api.open-meteo.com/v1/forecast", params=params
    )

    # Process the first response
    response = responses[0]

    # Process hourly data
    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
        "wind_speed_10m": hourly.Variables(2).ValuesAsNumpy(),
        "wind_direction_10m": hourly.Variables(3).ValuesAsNumpy(),
    }

    # Create and return the DataFrame
    hourly_dataframe = pd.DataFrame(data=hourly_data)
    return hourly_dataframe


def plot_current_location(df, show_data_transfer=False):
    # Filter entries with valid device latitude and longitude
    valid_entries = df[(df["latitude"] != 0) & (df["longitude"] != 0)]
    last_entry = valid_entries.head(1)

    if last_entry.empty:
        st.warning("No valid GPS coordinates found in the last hour.")
    else:
        # Get the latitude and longitude of the last location
        lat = last_entry["latitude"].iloc[0]
        lon = last_entry["longitude"].iloc[0]

        # Get the timestamp of the last refresh
        last_refreshed = last_entry["received_at"].iloc[0].strftime("%Y-%m-%d %H:%M:%S")

        # Create a folium map centered around the last known location
        if show_data_transfer:
            zoom = 11
        else:
            zoom = 15

        m = folium.Map(location=[lat, lon], zoom_start=zoom)

        # Add a marker for the last known location
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"Device Location<br>Latitude: {lat}, Longitude: {lon}<br>Last Refreshed: {last_refreshed}",
                max_width=300,
            ),
            icon=folium.Icon(
                color="blue", icon="ship", prefix="fa"
            ),  # Adjusted to 'anchor' as 'ship' might not be supported
        ).add_to(m)

    if show_data_transfer:
        # Check the count of gateways and mark their locations
        count_gw = last_entry["count_gw"].iloc[0]
        for i in range(1, count_gw + 1):
            lat_gw = last_entry[f"latitude_gw_{i}"].iloc[0]
            lon_gw = last_entry[f"longitude_gw_{i}"].iloc[0]
            snr_gw = last_entry[f"snr_gw_{i}"].iloc[0]
            rssi_gw = last_entry[f"rssi_gw_{i}"].iloc[0]
            name_gw = last_entry[f"id_gw_{i}"].iloc[0]

            # Determine line width based on SNR, mapping the range from -10 to -20 to a width in pixels
            line_width = 2 + ((-10 - snr_gw) * (5 - 1) / (10))

            if pd.notnull(lat_gw) and pd.notnull(lon_gw):  # Ensure gateway has valid coordinates
                folium.Marker(
                    location=[lat_gw, lon_gw],
                    popup=f"Gateway {name_gw}<br>Latitude: {lat_gw}, Longitude: {lon_gw}<br>SNR: {snr_gw} dB | RSSI: {rssi_gw} dBm",
                    icon=folium.Icon(color="green", icon="cloud"),
                ).add_to(m)

                # Calculate distance in meters
                distance_m = geodesic((lat, lon), (lat_gw, lon_gw)).meters

                # Draw line between device location and gateway
                line = folium.PolyLine(
                    locations=[(lat, lon), (lat_gw, lon_gw)],
                    color="red",
                    weight=line_width,
                ).add_to(m)

                # Add distance text to the line
                middle_point = [
                    (lat + lat_gw) / 2,
                    (lon + lon_gw) / 2
                ]
                folium.map.Marker(
                    middle_point,
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 9pt; font-weight: bold; color: white; background-color: black; height: 40px; width: 40px; border-radius: 20px; opacity: 0.75; display: flex; justify-content: center; align-items: center;">{int(distance_m)}m</div>'

                    )
                ).add_to(m)

        # Display the map using Streamlit
        st_folium(m, use_container_width=True, height=400)


def plot_history_location(df):
    # center the map on all the data points
    lat = df["latitude"].mean()
    lon = df["longitude"].mean()

    m = folium.Map(location=[lat, lon], zoom_start=15)

    # Prepare data for the heatmap (list of lat, lon pairs)
    heat_data = [[row["latitude"], row["longitude"]] for index, row in df.iterrows()]

    # Add a heatmap layer
    HeatMap(heat_data).add_to(m)

    # Add markers for the last location(s)
    # Assuming 'received_at' is sorted or the last row(s) represent the last locations
    last_rows = df.tail(1)  # Adjust this if you expect multiple "last" locations
    for index, row in last_rows.iterrows():
        lat = row["latitude"]
        lon = row["longitude"]
        last_refreshed = index.strftime("%Y-%m-%d %H:%M:%S")

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"Latitude: {lat}, Longitude: {lon}<br>Last Refreshed: {last_refreshed}",
                max_width=300,
            ),
            icon=folium.Icon(
                color="red", icon="info-sign"
            ),  # Markers in red to distinguish them
        ).add_to(m)

        # Display the map using Streamlit
    st_folium(m, use_container_width=True, height=400, returned_objects=[])


def show_current_measurements(df):
    st.subheader("Aktuelle Messwerte")
    st.info(
        "Die Messwerte könnten sehr ungenau oder falsch sein - muss noch genauer geprüft werden."
    )
    col1, col2 = st.columns((1, 1))

    with col1:
        st.metric("Feuchtigkeit", f"{df['humidity'].iloc[0]} %", delta=None)

    with col2:
        st.metric("Temperatur", f"{df['temperature'].iloc[0]} °C", delta=None)

    # with col3:
    #         st.metric("Battery Voltage", f"{df['batteryVoltage'].iloc[0]} V", delta=None)


def transform_history(bigquery_df, weather_df):
    # remove rows with missing latitude and longitude from the bigquery data
    bigquery_df = bigquery_df[
        (bigquery_df["latitude"] != 0) & (bigquery_df["longitude"] != 0)
    ]

    # aggregate the bigquery data to hourly averages
    bigquery_df = bigquery_df.resample("H", on="received_at").mean(numeric_only=True)

    # merge the bigquery data with the weather data
    df = pd.merge_asof(
        bigquery_df,
        weather_df,
        left_index=True,
        right_on="date",
        direction="nearest",
    )

    df = df.rename(
        columns={
            "temperature_2m": "Temperatur Romanshorn",
            "relative_humidity_2m": "Feuchtigkeit Romanshorn",
            "wind_speed_10m": "Windgeschwindigkeit Romanshorn",
            "wind_direction_10m": "Windrichtung Romanshorn",
            "temperature": "Temperatur Boot",
            "humidity": "Feuchtigkeit Boot",
        }
    )

    return df


def plot_history_weather_temp(df):
    # Create traces for each measurement
    trace1 = go.Scatter(
        x=df.index,
        y=df["Temperatur Romanshorn"],
        mode="lines+markers",
        name="Temperatur Romanshorn",
    )
    trace3 = go.Scatter(
        x=df.index,
        y=df["Temperatur Boot"],
        mode="lines+markers",
        name="Temperatur Boot",
    )

    # Combine traces into a list
    data = [trace1, trace3]

    # Define layout options
    layout = go.Layout(
        # title='Messungen über die Zeit',
        # xaxis=dict(
        #     title='Zeit (received_at)',
        #     tickformat='%d.%m',  # Day.Month format
        #     dtick="D1",  # One tick per day
        #     tickangle=-45,  # Rotate tick labels for better legibility
        # ),
        yaxis_title="Temperatur (°C)",
        margin=dict(
            l=20, r=20, t=40, b=60
        ),  # Adjust bottom margin to accommodate rotated labels
        hovermode="closest",
        legend=dict(
            x=0.5,
            y=-0.3,  # Adjust for legend positioning
            xanchor="center",
            yanchor="top",
            orientation="h",
        ),
    )

    # Create the figure with data and layout
    fig = go.Figure(data=data, layout=layout)

    # Displaying the plot in Streamlit
    st.plotly_chart(fig, use_container_width=True)


def plot_history_weather_hum(df):
    # Create traces for each measurement
    trace2 = go.Scatter(
        x=df.index,
        y=df["Feuchtigkeit Romanshorn"],
        mode="lines+markers",
        name="Feuchtigkeit Romanshorn",
    )
    trace4 = go.Scatter(
        x=df.index,
        y=df["Feuchtigkeit Boot"],
        mode="lines+markers",
        name="Feuchtigkeit Boot",
    )

    # Combine traces into a list
    data = [trace2, trace4]

    # Define layout options
    layout = go.Layout(
        # title='Messungen über die Zeit',
        # xaxis=dict(
        #     # title='Zeit (received_at)',
        #     tickformat='%d.%m',  # Day.Month format
        #     dtick="D1",  # One tick per day
        #     tickangle=-45,  # Rotate tick labels for better legibility
        # ),
        yaxis_title="Feuchtigkeit (%)",
        margin=dict(
            l=20, r=20, t=40, b=60
        ),  # Adjust bottom margin to accommodate rotated labels
        hovermode="closest",
        legend=dict(
            x=0.5,
            y=-0.3,  # Adjust for legend positioning
            xanchor="center",
            yanchor="top",
            orientation="h",
        ),
    )

    # Create the figure with data and layout
    fig = go.Figure(data=data, layout=layout)

    # Displaying the plot in Streamlit
    st.plotly_chart(fig, use_container_width=True)


def run_app():
    current_data = ttn.get_ttn_data(TTN_KEY)
    current_data["received_at"] = pd.to_datetime(current_data["received_at"])
    current_data = current_data.sort_values(by="received_at", ascending=False)

    st.info(
        f"Die Daten wurden zuletzt aktualisiert: {utc_to_cest_readable(current_data['received_at'].iloc[0])}"
    )

    current_data = utc_to_cest(current_data)

    st.subheader("Aktueller Standort des Bootes")
    show_data_transfer = st.checkbox("Datenübertragung anzeigen", value=True)
    if show_data_transfer:
        st.markdown("""
        **Legende der Karte:**
        - **Blauer Marker:** Standort des Bootes
        - **Grüne Marker:** Standort der letzen Gateways
        - **Rote Linien:** Verbindungslinien zwischen Boot und Gateways
        - **Linienstärke:** Signal-to-Noise Ratio (SNR) des Gateways
        """)
    plot_current_location(current_data, show_data_transfer)
    show_current_measurements(current_data)

    st.title("Historische Daten")
    st.info(
        "Diese Daten werden nur stündlich aktualisiert und sind daher nicht in Echtzeit."
    )

    select_time_range = st.selectbox(
        "Zeitraum auswählen",
        ["Letzte 7 Tage", "Letzte 30 Tage", "Letzte 3 Monate"],
    )

    if select_time_range == "Letzte 7 Tage":
        days = 7
        today = datetime.now().strftime("%Y-%m-%d")
        before = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    elif select_time_range == "Letzte 30 Tage":
        days = 30
        today = datetime.now().strftime("%Y-%m-%d")
        before = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    elif select_time_range == "Letzte 3 Monate":
        days = 90
        today = datetime.now().strftime("%Y-%m-%d")
        before = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    load_history = st.button(
        "Klicken um Historische Daten zu laden", use_container_width=True
    )
    if load_history:
        historical_data = history_data(today, before)
        historical_data = utc_to_cest(historical_data)

        df = transform_history(historical_data, fetch_weather_data(past_days=days))

        st.write("#### Standort")
        plot_history_location(df)

        st.write("#### Temperatur")
        plot_history_weather_temp(df)

        st.write("#### Feuchtigkeit")
        plot_history_weather_hum(df)


# Main app flow
if handle_authentication():
    run_app()

else:
    st.stop()  # Stop the app if authentication fails or hasn't been attempted
