import streamlit as st
import bigquery as bq

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

    st.title("👋 Welcome to Analytics Severin")
    st.text("In the sidebar you can find the different pages.")

def boat_data():   
    query="""
SELECT * 
FROM `seli-data-storage.data_storage_1.lora_iot` 
ORDER BY received_at DESC
LIMIT 20
"""
    df = bq.query_bigquery_return_df(query, origin='mobility')

    return df

df = boat_data()
st.dataframe(df)