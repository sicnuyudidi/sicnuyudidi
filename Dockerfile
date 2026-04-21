FROM python:3.11-slim
WORKDIR /app
COPY generate.py .
RUN pip install --no-cache-dir requests
ENTRYPOINT ["python", "generate.py"]
