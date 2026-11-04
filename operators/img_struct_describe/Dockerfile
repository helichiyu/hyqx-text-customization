FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY inference.py map.json ./
COPY img_struct_describe/ ./img_struct_describe/

ENV INPUT_DIR=/data/input OUTPUT_DIR=/data/outputs
RUN mkdir -p /data/input /data/outputs
EXPOSE 6288

CMD ["uvicorn", "inference:app", "--host", "0.0.0.0", "--port", "6288"]
