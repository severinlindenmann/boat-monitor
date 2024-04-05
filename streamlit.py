import streamlit as st
import bigquery as bq
import ttn
import datetime
import pandas as pd
from datetime import timedelta
import os

if __name__ == "__main__":
    st.set_page_config(
        page_title="Boat Monitor | by Severin",
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


# Main app flow
if handle_authentication():

    def get_current_timestamp_minus_one_hour():
        # Get the current UTC time
        current_time = datetime.datetime.utcnow()

        # Subtract 1 hour from the current time
        one_hour_ago = current_time - datetime.timedelta(hours=1)

        # Format the result as a string in the desired format
        timestamp = one_hour_ago.strftime("%Y-%m-%dT%H:%M:%SZ")

        return timestamp

    def get_lora_data():
        df = ttn.get_ttn_data(get_current_timestamp_minus_one_hour())
        return df

    def boat_data():
        query = """
    SELECT * 
    FROM `seli-data-storage.data_storage_1.lora_iot` 
    ORDER BY received_at DESC
    """
        df = bq.query_bigquery_return_df(query, origin="mobility")

        return df

    df = get_lora_data()

    st.title("Live Data")
    st.dataframe(df, use_container_width=True)

    df["received_at"] = pd.to_datetime(df["received_at"])
    df = df.sort_values(by="received_at", ascending=False)

    # Sort the DataFrame by 'received_at' in descending order to get the latest entry
    latest_entry = df.iloc[0]

    # Function to display the last entry and last update time
    def display_last_entry():
        # Create two columns for a more organized layout
        col1, col2, col3, col4 = st.columns(4)

        # Display the metrics in the first column
        with col1:
            st.metric(
                "Battery Voltage", f"{latest_entry['batteryVoltage']} V", delta=None
            )

        # Display the metrics in the second column
        with col2:
            st.metric("Humidity", f"{latest_entry['humidity']} %", delta=None)

        with col3:
            st.metric("Temperature", f"{latest_entry['temperature']} °C", delta=None)

        with col4:
            st.metric("Switch Status", latest_entry["reedSwitchStatus"])

        new_date_obj = latest_entry["received_at"] + timedelta(hours=1)
        formatted_date = new_date_obj.strftime("%d.%m.%Y %H:%M Uhr CEST")
        update_info = f"Last Data Update: {formatted_date}"
        st.info(update_info)

    # Check if either latitude or longitude is 0 and extract the last entry where both are not 0
    try:
        last_successful_entry = df[(df["latitude"] != 0) & (df["longitude"] != 0)].iloc[
            0
        ]

        # Extract the date from the last successful entry
        latest_gps_coordinates = {
            "latitude": last_successful_entry["latitude"],
            "longitude": last_successful_entry["longitude"],
        }

        last_successful_date = last_successful_entry["received_at"]

        st.title("Real-Time Data")
        st.map(pd.DataFrame([latest_gps_coordinates]))
        # Display the last successful update tim
        new_date_obj = last_successful_date + timedelta(hours=1)
        formatted_date = new_date_obj.strftime("%d.%m.%Y %H:%M Uhr CEST")
        # formatted_date = last_successful_date.strftime("%d.%m.%Y %H:%M Uhr CEST")
        st.info(f"Last Successful Location Update: {formatted_date}")
        display_last_entry()

        with st.expander("Show Raw Data"):
            st.write("Time is in UTC")
            st.dataframe(df, use_container_width=True)
    except IndexError:
        st.warning("No successful GPS coordinates found in the last hour.")
        display_last_entry()

    st.title("Historical Data")
    df = boat_data()

    st.write("Time is in UTC")
    st.dataframe(df, use_container_width=True)

else:
    st.stop()  # Stop the app if authentication fails or hasn't been attempted
