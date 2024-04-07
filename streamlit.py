import streamlit as st
import ttn
import json
import pandas as pd
from datetime import timedelta
import os
from dotenv import load_dotenv
from google.cloud import bigquery
import pydeck as pdk

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


def history_data():
    query = """
SELECT * FROM `seli-data-storage.data_storage_1.lora_iot` 
WHERE TIMESTAMP_TRUNC(received_at, DAY) > TIMESTAMP("2024-04-05")
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


def plot_current_location(df):
    # find the last entry with valid latitude and longitude
    df = df[(df["latitude"] != 0) & (df["longitude"] != 0)]
    df = df.head(1)
    if df.empty:
        st.warning("Keine gültigen GPS-Koordinaten in der letzten Stunde gefunden.")
    else:
        st.map(df)


def show_current_measurements(df):
    st.subheader("Aktuelle Messwerte")
    col1, col2 = st.columns((1, 1))

    with col1:
        st.metric("Feuchtigkeit", f"{df['humidity'].iloc[0]} %", delta=None)

    with col2:
        st.metric("Temperatur", f"{df['temperature'].iloc[0]} °C", delta=None)

    # with col3:
    #         st.metric("Battery Voltage", f"{df['batteryVoltage'].iloc[0]} V", delta=None)


def run_app():
    current_data = ttn.get_ttn_data(TTN_KEY)
    current_data["received_at"] = pd.to_datetime(current_data["received_at"])
    current_data = current_data.sort_values(by="received_at", ascending=False)

    st.info(
        f"Die Daten wurden zuletzt aktualisiert: {utc_to_cest_readable(current_data['received_at'].iloc[0])}"
    )

    st.subheader("Aktueller Standort")
    plot_current_location(current_data)
    show_current_measurements(current_data)

    st.title("Historische Daten")

    historical_data = history_data()
    historical_data = utc_to_cest(historical_data)

    st.write("#### Standort")
    # Define the map layer for the boat's movement
    layer = pdk.Layer(
        "ScatterplotLayer",
        historical_data,
        get_position=["longitude", "latitude"],
        auto_highlight=True,
        get_radius=100,  # Radius of each data point
        get_fill_color=[180, 0, 200, 140],  # Color of the data points
        pickable=True,
    )

    # Define the view state for the map
    view_state = pdk.ViewState(
        latitude=historical_data["latitude"].mean(),
        longitude=historical_data["longitude"].mean(),
        zoom=14,
        pitch=0,
    )

    # Render the map with pydeck
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

    st.write("#### Temperatur und Feuchtigkeit")
    st.line_chart(historical_data[["temperature", "humidity"]])


# Main app flow
if handle_authentication():
    run_app()

else:
    st.stop()  # Stop the app if authentication fails or hasn't been attempted
