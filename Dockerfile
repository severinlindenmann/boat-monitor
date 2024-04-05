# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11.2-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app

RUN pip install -U pip
RUN pip install -r requirements.txt

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit.py", "--server.port=8080", "--server.headless=true", "--browser.gatherUsageStats=false"]
