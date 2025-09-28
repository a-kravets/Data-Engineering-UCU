FROM python:3.11-slim
WORKDIR /app
RUN pip install flask requests
COPY service.py .
EXPOSE 8000
CMD ["python", "service.py"]
