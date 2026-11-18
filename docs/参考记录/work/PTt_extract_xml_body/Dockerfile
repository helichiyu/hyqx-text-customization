# PTt_extract_xml_body 镜像（构建上下文 = pretrain_text/ 仓库根目录）
# 构建：docker build -f PTt_extract_xml_body/Dockerfile -t ptt_extract_xml_body:1.0.0 .

FROM python:3.10-slim

LABEL description="预训练文本产线算子：XML抽出正文（规则型）"

WORKDIR /srv/operator

COPY common/ /srv/common/
COPY PTt_extract_xml_body/ /srv/operator/

# 认证拦截（规范 3.4）：默认摘要对应联调令牌 pretrain-text-pool-dev，生产必须覆盖为本环境摘要
# python -c "import hashlib;print(hashlib.sha256('你的令牌'.encode()).hexdigest())"
ENV AUTH_TOKEN_SHA256=332772ef2a89ed815aff796e04f5c706d10cc000097cf557335f81546295fcd1

ENV PYTHONPATH=/srv:/srv/operator \
    PYTHONUNBUFFERED=1 \
    WORKERS=2

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 6303

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:6303/health')" || exit 1

# 规范 11.2：多 worker 部署
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker -w ${WORKERS} -b 0.0.0.0:6303 inference:app"]
