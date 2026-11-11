FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    INPUT_DIR=/data/input \
    OUTPUT_DIR=/data/outputs

# nginx 只做路径路由（/<算子名>/... → 本地独立 uvicorn 进程）。
# 显式 noninteractive，并把 apt 源换到阿里云，避免 deb.debian.org 在部分网络下长时间卡住。
RUN export DEBIAN_FRONTEND=noninteractive \
    && sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# 使用清华 PyPI 镜像，避免 pypi.org 大索引在部分网络下超时。
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY nginx.conf supervisor.py ./
COPY ops/ ./ops/

RUN mkdir -p /data/input /data/outputs

EXPOSE 17022

CMD ["python", "/app/supervisor.py"]
