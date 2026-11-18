"""PTt_extract_pdf_body 服务入口。

薄入口：HTTP 壳与公共逻辑在 common/，核心算法在 model/network.py。
开发模式：python inference.py --port 6304
生产模式：gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:6304 inference:app
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _path in (_ROOT, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from common.server import create_app, run_service  # noqa: E402
from model.network import OPERATOR_CLASS  # noqa: E402

OPERATOR = OPERATOR_CLASS()
app = create_app(OPERATOR)

if __name__ == "__main__":
    run_service(OPERATOR, default_port=6304)
