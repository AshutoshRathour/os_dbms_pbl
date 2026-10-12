FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir Pillow==10.4.0
COPY process.py .
ENTRYPOINT ["python", "process.py"]
