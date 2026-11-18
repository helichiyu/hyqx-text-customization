# 预训练文本算子池镜像（联调部署形态，对外 17014）
# 构建：docker build -t op-pretrain-text-pool:1.0.0 .
# 运行：docker compose up -d（见 docker-compose.yml）
# 池内算子启动时自动发现：复制 PTt_xxx 算子目录进本仓库即扩充，
# 其 Python 依赖在 requirements-pool.txt 中对应段落启用

FROM python:3.10-slim

LABEL description="预训练文本产线算子池（正文提取组，/predict?detection=PTt_xxx 路由）"

WORKDIR /srv/pool

# #7 旧版 .doc 提取需要 LibreOffice（先装系统依赖）
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-pool.txt .
RUN pip install --no-cache-dir \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        -r requirements-pool.txt

# —— 复制含模型算子（#17 敏感检测 / #26 MLM / #37 Token序列）回来时启用：
# CPU 版 torch 显著减小镜像（GPU 环境改用官方源重装）
# RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
# —— #20 英文模型/NLTK 数据：尽力下载，失败时算子自动降级规则引擎
# RUN python -m spacy download en_core_web_sm || true
# RUN python -c "import nltk; nltk.download('wordnet', quiet=True); nltk.download('omw-1.4', quiet=True)" || true

COPY . .

# 认证拦截（规范 3.4）：默认摘要对应联调令牌 pretrain-text-pool-dev。
# 生产部署必须覆盖为本环境令牌的摘要——镜像与配置只落摘要、不落明文：
#   python -c "import hashlib;print(hashlib.sha256('你的令牌'.encode()).hexdigest())"
# K8S 亦可用 Secret 注入 AUTH_TOKEN（摘要变量 AUTH_TOKEN_SHA256 优先）
ENV AUTH_TOKEN_SHA256=332772ef2a89ed815aff796e04f5c706d10cc000097cf557335f81546295fcd1

ENV PYTHONPATH=/srv/pool \
    PYTHONUNBUFFERED=1 \
    WORKERS=4 \
    MAX_INPUT_MB=10 \
    MAX_RESPONSE_MB=50

EXPOSE 17014

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:17014/health')" || exit 1

# 规范 11.2：多 worker 部署（池内模型/词典为进程级只读单例）
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker -w ${WORKERS} -b 0.0.0.0:17014 inference:app"]
