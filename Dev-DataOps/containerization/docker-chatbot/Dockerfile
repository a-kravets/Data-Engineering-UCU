FROM python:3.10-slim

WORKDIR /app

RUN pip install streamlit requests

COPY . /app

EXPOSE 8050

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8050", "--server.address=0.0.0.0"]
