import streamlit as st
from google.cloud import bigquery
import os

PROJECT = os.getenv("PROJECT")

@st.cache_resource
def create_bigquery_connection():
    return bigquery.Client(project=PROJECT)


@st.cache_data
def query_bigquery_return_df(query, origin="unknown"):
    try:
        os.mkdir("debug")
    except FileExistsError:
        print("debug folder exists")
    with open(f"debug/{origin}.sql", "w") as text_file:
        text_file.write(query)
    query_job = create_bigquery_connection().query(query)
    results = query_job.result()
    return results.to_dataframe()
