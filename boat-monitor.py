import streamlit as st
import bigquery as bq
import ttn
import datetime
import pandas as pd
from datetime import timedelta
import matplotlib.pyplot as plt

if __name__ == "__main__":
    st.set_page_config(
        page_title="Boat Monitor | by Severin",
        page_icon="👋",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://severin.io',
            'Report a bug': "https://severin.io",
            'About': "Boat Dashboard, Created by Severin Lindenmann"
        }
    )

    st.title("⛵ Easy | Boat Monitor")

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
    query="""
SELECT * 
FROM `seli-data-storage.data_storage_1.lora_iot` 
ORDER BY received_at DESC
"""
    df = bq.query_bigquery_return_df(query, origin='mobility')

    return df


df = get_lora_data()

df['received_at'] = pd.to_datetime(df['received_at'])
df = df.sort_values(by='received_at', ascending=False)

# Sort the DataFrame by 'received_at' in descending order to get the latest entry
latest_entry = df.iloc[0]

# Check if either latitude or longitude is 0 and extract the last entry where both are not 0
last_successful_entry = df[(df['latitude'] != 0) & (df['longitude'] != 0)].iloc[0]

# Extract the date from the last successful entry
latest_gps_coordinates = {
    'latitude': last_successful_entry['latitude'],
    'longitude': last_successful_entry['longitude']
}

last_successful_date = last_successful_entry['received_at']

# Function to display the last entry and last update time
def display_last_entry():
    # Create two columns for a more organized layout
    col1, col2, col3, col4 = st.columns(4)
    
    # Display the metrics in the first column
    with col1:
        st.metric("Battery Voltage", f"{latest_entry['batteryVoltage']} V", delta=None)

    # Display the metrics in the second column
    with col2:
        st.metric("Humidity", f"{latest_entry['humidity']} %", delta=None)

    with col3:
        st.metric("Temperature", f"{latest_entry['temperature']} °C", delta=None)

    with col4:
        st.metric("Switch Status", latest_entry['reedSwitchStatus'])

    new_date_obj = latest_entry['received_at'] + timedelta(hours=1)
    formatted_date = new_date_obj.strftime("%d.%m.%Y %H:%M Uhr CEST")
    update_info = f"Last Data Update: {formatted_date}"
    st.info(update_info)
    

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


st.title("Historical Data")
df = boat_data()

# Set the 'received_at' column as the DataFrame index
df.set_index('received_at', inplace=True)

st.title('Temperature Chart')

# Create a custom plot with resized y-axis
fig, ax = plt.subplots()
ax.plot(df.index, df['temperature'])

# Set the y-axis limit to customize the range
y_min = min(df['temperature']) - 0.1
y_max = max(df['temperature']) + 0.1
ax.set_ylim(y_min, y_max)

# Set labels
ax.set_xlabel('Date')
ax.set_ylabel('Temperature')

# Display the plot in Streamlit
st.pyplot(fig)

st.write("Time is in UTC")
st.dataframe(df, use_container_width=True)