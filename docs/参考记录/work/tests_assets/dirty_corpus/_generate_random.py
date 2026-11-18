# -*- coding: utf-8 -*-
"""随机混合脏数据生成器：模拟真实爬取转储（好坏记录自然掺杂）。

重跑可换 SEED 获得新批次。文件级"脏度档案"随机（缺陷率 0~40%、
随机缺陷种类子集），记录长度近自然分布（多数短、少数长、个别超长）。
mojibake 缺陷已剔除换行类控制符，避免破坏 JSONL 行结构。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).parent
SEED = 20261011
rng = random.Random(SEED)

# ---------------- 语料池 ----------------
SENTENCES = {
    "科技": [
        "{}公司今日发布新一代{}产品，官方称整体性能较上一代提升约{}%。",
        "研究团队在{}领域取得进展，相关论文已提交至国际会议评审。",
        "该{}平台目前注册用户超过{}万，日均处理请求达{}亿次。",
        "工程师介绍，新架构将{}模块的响应时间缩短了一半以上。",
    ],
    "财经": [
        "今日收盘，{}指数上涨{}%，板块内多数个股飘红。",
        "机构报告指出，{}行业下半年出口订单环比增长{}%。",
        "{}公司发布年报，营业收入{}亿元，同比增长{}%。",
        "市场分析认为，利率变化将对{}类资产估值带来短期扰动。",
    ],
    "健康": [
        "专家提示，{}人群每日摄入足量蔬果有助于心血管健康。",
        "研究表明，每周进行{}次中等强度运动可降低{}风险。",
        "入冬后{}就诊人数上升，医生建议注意保暖与通风。",
    ],
    "体育": [
        "昨晚比赛中，{}队凭借第{}分钟的进球以{}比{}战胜对手。",
        "{}运动员在决赛中以{}米的成绩刷新个人最好成绩。",
        "联赛还剩{}轮，积分榜前列争夺进入白热化。",
    ],
    "教育": [
        "今年{}地区报名人数达{}万人，再创历史新高。",
        "新课程标准强调{}能力培养，试点学校反响积极。",
        "{}大学宣布增设{}方向硕士项目，明年起招生。",
    ],
    "民生": [
        "{}市地铁{}号线今日开通，初期运营间隔{}分钟。",
        "气象部门预计本周末{}地区将出现{}天气，提醒市民合理安排出行。",
        "社区服务中心新增{}项便民业务，办理时间大幅缩短。",
    ],
}
FILL = {
    "科技": ["星辰", "云图", "极目", "远航", "量子", "灵犀"],
    "财经": ["沪深300", "创业板", "恒生", "纳斯达克"],
    "健康": ["老年", "上班簇", "青少年", "产后恢复"],
    "体育": ["江城", "川联", "岭南", "北岭"],
    "教育": ["本市", "沿江省份", "试点区"],
    "民生": ["临江", "云溪", "望城", "海棠"],
}
NUMS = ["12", "35", "78", "120", "640", "1500", "8"]
AD_PHRASES = [
    "点击下载APP领取新人红包！", "关注公众号【天天福利社】获取完整版资料。",
    "加微信 kefu888a 免费咨询，前十名享内部价。", "限时特惠！全场一折起，错过再等一年！",
    "扫码进群，每日推送稳赚项目。", "广告位招租，联系QQ：123456789。",
]
URL_POOL = [
    "https://example.com/news/2026/detail?id={}", "http://data.example.org/download/{}",
    "https://www.example-data.cn/article/{}", "www.{}.info/read?page=3",
]
WATERMARKS = [
    "——本文转自示例资讯APP", "更多精彩内容请下载XX头条", "声明：本文由平台自动抓取",
    "第1页 共{}页  版权所有", "责任编辑：系统抓取",
]
SURNAMES = "王李张刘陈杨赵黄周吴徐孙马朱胡郭何高林"
GIVEN = "伟芳娜敏静磊军洋勇艳杰娟涛明超秀霞平刚桂英"
HTML_WRAPS = ['<p style="margin:0">{}</p>', "<div>{}</div>", '<span class="content">{}</span>', "{}<br/>"]
EMOJI = "🔥💥💯🙏😂🤝👍✨"

# 换行类/控制符（NEL/LS/PS/VT/FF 等）：出现在 JSONL 行内会破坏 splitlines。
_LINE_BREAKERS = {0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85, 0x2028, 0x2029}


def rand_sentence(topic: str) -> str:
    tpl = rng.choice(SENTENCES[topic])
    holes = tpl.count("{}")
    parts = []
    for _ in range(holes):
        r = rng.random()
        if r < 0.4:
            parts.append(rng.choice(FILL[topic]))
        elif r < 0.85:
            parts.append(rng.choice(NUMS))
        else:
            parts.append(f"{rng.randint(2, 99)}")
    try:
        return tpl.format(*parts)
    except IndexError:
        return tpl


def rand_record_text() -> str:
    topic = rng.choice(list(SENTENCES))
    n = max(1, int(rng.lognormvariate(0.9, 0.8)))  # 多数 1-8 句，长尾到几十句
    n = min(n, 40)
    return "".join(rand_sentence(topic) for _ in range(n))


def rand_pii() -> str:
    name = rng.choice(SURNAMES) + rng.choice(GIVEN)
    phone = f"1{rng.choice('3456789')}{''.join(rng.choice('0123456789') for _ in range(9))}"
    idcard = "".join(rng.choice("0123456789") for _ in range(17)) + rng.choice("0123456789X")
    mail = f"user{rng.randint(100, 999)}@example.com"
    return f"联系人{name}，电话{phone}，证件号{idcard}，邮箱{mail}。"


def _latin1_garble(text: str) -> str:
    """UTF-8→Latin-1 转写乱码，剔除换行类控制符以免破坏 JSONL 行。"""
    garbled = text.encode("utf-8").decode("latin-1", errors="replace")
    return "".join(ch for ch in garbled if ord(ch) not in _LINE_BREAKERS and ord(ch) >= 0x20 or ch == "\t")


def apply_defect(text: str, kind: str) -> str:
    if kind == "ad":
        return f"{text}{rng.choice(AD_PHRASES)}"
    if kind == "url":
        url = rng.choice(URL_POOL)
        return f"{text}详情见{url.format(rng.randint(1000, 9999))}"
    if kind == "short":
        return text[: rng.randint(1, 8)]
    if kind == "repeat":
        return rng.choice(text or "哈") * rng.randint(15, 50)
    if kind == "typo":
        chars = list(text)
        for i in range(0, len(chars) - 1, max(3, len(chars) // 12)):
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return "".join(chars)
    if kind == "fullwidth":
        return "".join(
            chr(ord(ch) + 0xFEE0) if ch.isascii() and ch.isalnum() and rng.random() < 0.5 else ch
            for ch in text
        )
    if kind == "mojibake":
        cut = int(len(text) * 0.6)
        return text[:cut] + _latin1_garble(text[cut:])
    if kind == "zwsp":
        out, cnt = [], 0
        for ch in text:
            out.append(ch)
            cnt += 1
            if cnt % 9 == 0 and rng.random() < 0.5:
                out.append(rng.choice(["​", "‌", "­"]))
        return "".join(out)
    if kind == "pii":
        return f"{text}{rand_pii()}"
    if kind == "watermark":
        return f"{text}{rng.choice(WATERMARKS).format(rng.randint(2, 9))}"
    if kind == "html":
        return rng.choice(HTML_WRAPS).format(text)
    if kind == "emoji":
        return f"{text}{''.join(rng.choice(EMOJI) for _ in range(rng.randint(4, 12)))}"
    if kind == "bloat":
        return text + ("为模型训练提供高质量语料支撑的补充论述段落。" * rng.randint(150, 350))
    if kind == "truncate":
        pos = int(len(text) * rng.uniform(0.15, 0.5))
        return text[:pos]
    return text


DEFECT_KINDS = ["ad", "url", "short", "repeat", "typo", "fullwidth", "mojibake",
                "zwsp", "pii", "watermark", "html", "emoji", "bloat", "truncate"]


def make_batch(records: int, defect_rate: float, kinds: list[str]) -> list[dict]:
    rows, seen = [], []
    for i in range(records):
        rid = f"r{rng.randint(10000, 99999)}_{i:03d}"
        text = rand_record_text()
        if rng.random() < defect_rate:
            text = apply_defect(text, rng.choice(kinds))
        row = {"id": rid, "text": text}
        # 自然重复：3% 概率直接复用前面的记录
        if seen and rng.random() < 0.03:
            row = dict(rng.choice(seen))
            row["id"] = rid
        rows.append(row)
        seen.append(row)
    return rows


def dump_jsonl(name: str, rows: list[dict]) -> None:
    (OUT / name).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8", newline=""
    )


# ---------------- 批次生成：18 个随机档案的 jsonl ----------------
profiles = []
for i in range(1, 19):
    rate = rng.choice([0.0, 0.05, 0.08, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4])
    kinds = rng.sample(DEFECT_KINDS, rng.randint(3, 7)) if rate else []
    profiles.append((rate, kinds))

shared_pool: list[dict] = []
for idx, (rate, kinds) in enumerate(profiles, 1):
    rows = make_batch(rng.randint(6, 60), rate, kinds)
    # 跨文件重复：随机两批之间共享 1~3 条记录（模拟镜像站抓取）
    if idx % 4 == 0 and shared_pool:
        for row in rng.sample(shared_pool, min(len(shared_pool), rng.randint(1, 3))):
            rows.insert(rng.randint(0, len(rows)), dict(row, id=f"x{row['id'][1:]}_{idx:02d}"))
    else:
        shared_pool.extend(rows[: max(1, len(rows) // 4)])
    dump_jsonl(f"rnd{idx:02d}_mix.jsonl", rows)

# ---------------- 特化批次 ----------------
reviews, base_reviews = [], [
    "物流很快，包装完好，客服态度也不错，下次还会回购。",
    "用了三天，续航一般，其他方面符合预期。",
    "性价比高，家里人都在用，推荐给同事了。",
    "收到时外盒有点压痕，客服补发及时，点赞。",
]
for i in range(rng.randint(35, 55)):
    t = rng.choice(base_reviews)
    if rng.random() < 0.15:
        t = apply_defect(t, "emoji")
    reviews.append({"id": f"rev{i:03d}", "rating": rng.randint(1, 5), "text": t})
dump_jsonl("rnd19_reviews.jsonl", reviews)

chat_lines = []
for _ in range(rng.randint(40, 70)):
    who = rng.choice(["群友A", "群友B", "路人甲", "——", "管理员"])
    msg = rng.choice([
        rand_sentence(rng.choice(list(SENTENCES))),
        "哈哈哈哈哈哈哈",
        "666",
        "楼上说得对",
        "[表情][图片]",
        "有人看过这个吗 www.example.com/read/8213",
        "私我 私我",
        "🤝🤝🤝",
    ])
    chat_lines.append(f"{who}：{msg}")
(OUT / "rnd20_chatlog.txt").write_text("\n".join(chat_lines), encoding="utf-8", newline="")

digest = []
for t in list(SENTENCES)[:4]:
    for _ in range(rng.randint(3, 7)):
        digest.append(rand_sentence(t))
        if rng.random() < 0.2:
            digest.append(rng.choice(WATERMARKS).format(rng.randint(2, 9)))
(OUT / "rnd21_digest.txt").write_text("\n".join(digest), encoding="utf-8", newline="")

rows = make_batch(12, 0.1, ["url", "short"])
lines = [json.dumps(r, ensure_ascii=False) for r in rows]
broken = rng.randint(2, 5)
lines.insert(broken, lines[broken][: int(len(lines[broken]) * 0.7)])  # 截断的半行 JSON
(OUT / "rnd22_truncated.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")

frags = []
for _ in range(rng.randint(6, 12)):
    text = rand_record_text()
    frags.append(rng.choice(HTML_WRAPS).format(text))
    if rng.random() < 0.3:
        frags.append(f'<a href="http://ad.example.com/track?id={rng.randint(100, 999)}">推广</a>')
(OUT / "rnd23_html_frag.html").write_text("\n".join(frags), encoding="utf-8", newline="")

xml_ok = '<?xml version="1.0"?>\n<docs batch="rnd24" src="crawl">\n'
for i in range(rng.randint(5, 10)):
    inner = rand_record_text().replace("&", "＆")
    xml_ok += f'  <doc id="{1000 + i}" lang="zh" grabbed="2026-10-{rng.randint(1, 9):02d}"><body><![CDATA[{inner}]]></body></doc>\n'
xml_ok += "</docs>\n"
(OUT / "rnd24_feed.xml").write_text(xml_ok, encoding="utf-8", newline="")
(OUT / "rnd25_bad_xml.xml").write_text(
    xml_ok[: int(len(xml_ok) * 0.82)] + "</docs>", encoding="utf-8", newline=""
)

csv_rows = ["id,content,source"]
for i, r in enumerate(make_batch(rng.randint(8, 15), 0.1, ["ad", "typo"]), 1):
    content = r["text"].replace('"', "”")
    if rng.random() < 0.3:
        content = f'"{content},多打了一个逗号'
    csv_rows.append(f'{i},{content},crawl-{rng.randint(100, 999)}')
(OUT / "rnd26_messy.csv").write_text("\n".join(csv_rows), encoding="utf-8", newline="")

forum = []
for i in range(rng.randint(10, 20)):
    body = rand_record_text()
    if rng.random() < 0.35:
        body = f">> 引用第{rng.randint(1, 9)}楼：{rand_sentence('科技')[:12]}……\n{body}"
    if rng.random() < 0.25:
        body += rng.choice(AD_PHRASES)
    forum.append({"id": f"post{i:03d}", "floor": i + 1, "text": body})
dump_jsonl("rnd27_forum.jsonl", forum)

total = len(list(OUT.glob("rnd*")))
print(f"SEED={SEED} rnd files: {total}")
