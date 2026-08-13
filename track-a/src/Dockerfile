FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY crawl_knx_devices.py .

# Container chạy xong 1 lần rồi thoát (job, không phải service sống).
# n8n trigger theo lịch bằng: docker compose run --rm registry-crawler
# Output ghi vào /data (mount volume ngoài để lấy file CSV ra, xem docker-compose.snippet.yml).
ENTRYPOINT ["python3", "crawl_knx_devices.py"]
CMD ["--output", "/data/knx_devices_baseline.csv"]
