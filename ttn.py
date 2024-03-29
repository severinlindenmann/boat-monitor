import streamlit as st
import requests
import json
import os
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

TTN_KEY = os.getenv('TTN_KEY')

@st.cache_resource
def retrieve_stored_uplinks(api_key, application_id, timestamp):
    url = f"https://eu1.cloud.thethings.network/api/v3/as/applications/{application_id}/packages/storage/uplink_message"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream"
    }
    params = {
        "after": timestamp
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.text
    else:
        return f"Error: {response.status_code}"

def get_ttn_data(timestamp):
  result = retrieve_stored_uplinks(TTN_KEY, "lora-test-sli1", timestamp)

  # Split the string by lines and filter out empty lines
  json_strings = [line for line in result.split('\n') if line.strip()]

  # Parse each JSON string into a dictionary
  dict_list = []
  for json_str in json_strings:
      try:
          dict_list.append(json.loads(json_str))
      except json.JSONDecodeError as e:
          print(f"Error decoding JSON: {e}")

  # Extract data from the JSON and create a list of dictionaries
  extracted_data = []
  for entry in dict_list:
      extracted_entry = {
          'received_at': entry['result']['received_at'],
          'batteryVoltage': entry['result']['uplink_message']['decoded_payload']['batteryVoltage'],
          'humidity': entry['result']['uplink_message']['decoded_payload']['humidity'],
          'latitude': entry['result']['uplink_message']['decoded_payload']['latitude'],
          'longitude': entry['result']['uplink_message']['decoded_payload']['longitude'],
          'reedSwitchStatus': entry['result']['uplink_message']['decoded_payload']['reedSwitchStatus'],
          'satellites': entry['result']['uplink_message']['decoded_payload']['satellites'],
          'temperature': entry['result']['uplink_message']['decoded_payload']['temperature'],
      }
      extracted_data.append(extracted_entry)

  # Create a DataFrame
  return pd.DataFrame(extracted_data)