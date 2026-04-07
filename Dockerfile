FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
# This tells Google Cloud to run the Flask app using Gunicorn on port 8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
