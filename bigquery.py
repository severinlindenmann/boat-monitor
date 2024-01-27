import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import json
import os

from dotenv import load_dotenv
load_dotenv()

DEBUG = os.getenv('DEBUG')


@st.cache_resource
def create_bigquery_connection():

    GOOGLE_KEY_JSON = os.getenv('GOOGLE_KEY_JSON')
    GOOGLE_KEY_JSON = json.loads(GOOGLE_KEY_JSON)

    credentials = service_account.Credentials.from_service_account_info(
        GOOGLE_KEY_JSON)
    return bigquery.Client(credentials=credentials, project=GOOGLE_KEY_JSON['project_id'])


@st.cache_data
def query_bigquery_return_df(query, origin='unknown'):

    # creates a sql file for debugging and testing
    if DEBUG == 'TRUE':
        try:
            os.mkdir('debug')
        except FileExistsError:
            print('debug folder exists')

        with open(f"debug/{origin}.sql", "w") as text_file:
            text_file.write(query)

    query_job = create_bigquery_connection().query(query)
    results = query_job.result()
    return results.to_dataframe()
