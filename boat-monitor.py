import streamlit as st
import bigquery as bq
import pandas as pd

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

def mobility():   
    query="""
SELECT
  *
FROM
  `seli-data-storage.data_storage_1.free_bike_status`
WHERE
  DATE(refresh_time) = "2023-03-10"
  AND TIMESTAMP(crawl_time) = (
  SELECT
    crawl_time
  FROM
    `seli-data-storage.data_storage_1.free_bike_status`
  WHERE
    DATE(refresh_time) = "2023-03-10"
  ORDER BY
    crawl_time DESC
  LIMIT
    1)
"""
    df = bq.query_bigquery_return_df(query, origin='mobility')

    return df

df = mobility()
unique_providers = df['provider_id'].unique()
col1,col2,col3,col4 = st.columns(4)
col1.metric('Unique Providers',len(unique_providers))
col2.metric('Bikes and Scooters',len(df['bike_id'].unique()))
col3.metric('Are reserved',len(df[df['is_reserved']]))
col4.metric('Are Disabled',len(df[df['is_disabled']]))

st.bar_chart(df.groupby('provider_id')['bike_id'].count())
st.dataframe(unique_providers)
st.dataframe(df)