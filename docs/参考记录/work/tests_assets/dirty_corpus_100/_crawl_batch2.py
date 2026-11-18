# -*- coding: utf-8 -*-
"""第二批真实数据爬取：多源列表页 → 抽取文章链接 → 批量下载原始页面。

产出文件直接落在 dirty_corpus/，并写 _crawl_log.jsonl 清单（url/字节/时间）。
"""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent
LOG = OUT / "_crawl_log.jsonl"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

existing_urls: set[str] = set()
if LOG.exists():
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing_urls.add(json.loads(line)["url"])
            except Exception:
                pass


def fetch(url: str, timeout: int = 20) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
                if resp.status != 200:
                    raise IOError(f"status {resp.status}")
                data = resp.read()
                return data if len(data) > 3000 else None  # 过滤错误页/空页
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.0)


def log(file: str, url: str, size: int) -> None:
    with LOG.open("a", encoding="utf-8", newline="\n") as h:
        h.write(json.dumps({"file": file, "url": url, "bytes": size, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False) + "\n")


def links_in(html: str, pattern: str, base: str | None = None) -> list[str]:
    found = re.findall(pattern, html)
    out, seen = [], set()
    for u in found:
        u = u.strip(" \"'()").split("#")[0]
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/") and base:
            u = base + u
        elif u.startswith("/"):
            continue
        if u in seen or u in existing_urls:
            continue
        seen.add(u)
        out.append(u)
    return out


def grab(listing_urls: list[str], pattern: str, count: int, prefix: str, ext: str = "html", base: str | None = None) -> int:
    candidates: list[str] = []
    for lu in listing_urls:
        data = fetch(lu)
        print(f"  listing {lu[:48]} -> {len(data) if data else 0}B")
        if data:
            try:
                html = data.decode("utf-8", errors="replace")
            except Exception:
                continue
            candidates.extend(links_in(html, pattern, base))
        if len(candidates) >= count * 2:
            break
    got = len(list(OUT.glob(f"{prefix}_*")))
    for url in candidates:
        if got >= count:
            break
        data = fetch(url)
        if not data:
            continue
        name = f"{prefix}_{got + 1:02d}.{ext}"
        (OUT / name).write_bytes(data)
        log(name, url, len(data))
        got += 1
        time.sleep(0.3)
    print(f"{prefix}: {got}/{count}")
    return got


# 1. 中新网滚动列表（翻 3 页，跨频道）
grab(
    [f"https://www.chinanews.com.cn/scroll-news/news{i}.html" for i in (1, 2, 3)],
    r'(?:https?:)?//www\.chinanews\.com\.cn/\w+/2026/\d+-\d+/\d+\.shtml',
    15, "chinanews2",
)
# 2. 博客园首页（真实技术博客，侧栏/推荐噪声足）
grab(
    ["https://www.cnblogs.com/sitehome/p/1", "https://www.cnblogs.com/sitehome/p/2"],
    r'(?:https?:)?//www\.cnblogs\.com/[\w-]+/p/\d+[^\x22\x27\s]*',
    12, "cnblogs",
)
# 3. 人民网首页各频道文章
grab(
    ["http://www.people.com.cn/", "http://politics.people.com.cn/"],
    r'(?:https?:)?//\w+\.people\.com\.cn/n1/2026/\d+/c\d+-\d+\.html',
    10, "people",
)
# 4. 新华网首页
grab(
    ["http://www.xinhuanet.com/", "http://www.news.cn/politics/"],
    r'(?:https?:)?//www\.news\.cn/[^\x22\x27\s]*?c_\d+\.htm',
    10, "xinhua",
)
# 5. 开源中国资讯
grab(
    ["https://www.oschina.net/news"],
    r'https?://www\.oschina\.net/news/\d+',
    10, "oschina",
)
# 6. 思否资讯
grab(
    ["https://segmentfault.com/news"],
    r'/a/\d+',
    8, "segfault", base="https://segmentfault.com",
)
# 7. 东方财富证券要闻
grab(
    ["https://finance.eastmoney.com/a/czqyw.html"],
    r'https?://finance\.eastmoney\.com/a/\d+\.html',
    8, "eastmoney",
)

# 8. 固定教程页（w3school / python docs）
fixed = {
    "w3school_01.html": "https://www.w3school.com.cn/html/index.asp",
    "w3school_02.html": "https://www.w3school.com.cn/css/index.asp",
    "w3school_03.html": "https://www.w3school.com.cn/js/index.asp",
    "w3school_04.html": "https://www.w3school.com.cn/sql/index.asp",
    "w3school_05.html": "https://www.w3school.com.cn/php/index.asp",
    "pydocs_01.html": "https://docs.python.org/3/whatsnew/3.12.html",
    "pydocs_02.html": "https://docs.python.org/3/tutorial/datastructures.html",
    "pydocs_03.html": "https://docs.python.org/3/library/json.html",
    "pydocs_04.html": "https://docs.python.org/3/reference/expressions.html",
}
for name, url in fixed.items():
    data = fetch(url)
    if data:
        (OUT / name).write_bytes(data)
        log(name, url, len(data))
        print(f"{name}: {len(data)}B")

# 9. 真 XML 语料：中新网滚动 RSS
data = fetch("https://www.chinanews.com.cn/rss/scroll-news.xml")
if data:
    (OUT / "rss_chinanews_scroll.xml").write_bytes(data)
    log("rss_chinanews_scroll.xml", "https://www.chinanews.com.cn/rss/scroll-news.xml", len(data))
    print(f"rss_chinanews_scroll.xml: {len(data)}B")

print("done")
