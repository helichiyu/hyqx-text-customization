"""文本元信息线小样本：新闻 2 篇 + 非新闻 3 篇（产品页/教程/导航列表）HTML。"""

from __future__ import annotations

import argparse
from pathlib import Path

SAMPLES: dict[str, str] = {
    "news_001.html": """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>某市地铁3号线正式通车运营</title></head>
<body>
<h1>某市地铁3号线正式通车运营</h1>
<p class="meta">来源：某市日报　发布时间：2026年6月12日</p>
<p>本报讯（记者张伟）6月12日上午，某市地铁3号线通车仪式在市政府广场举行。市委常委、常务副市长李强出席仪式并宣布通车。</p>
<p>地铁3号线全长42.5公里，设站31座，连接高新区与老城核心区，总投资约380亿元。线路于2021年3月开工建设，历时5年建成。</p>
<p>市交通委主任王芳介绍，3号线开通后，沿线高峰时段通勤时间将缩短约40分钟，预计日均客流60万人次。</p>
<p>据悉，某市年内还将启动地铁7号线前期工作，进一步加密轨道交通网络。</p>
</body></html>""",
    "news_002.html": """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>某新能源企业与高校签署合作协议</title></head>
<body>
<h1>某新能源企业与高校签署战略合作协议</h1>
<p class="meta">来源：企业新闻网　2026年7月3日</p>
<p>7月3日，某新能源科技集团与某工业大学在市会展中心举行战略合作签约仪式。集团董事长陈明与校长周建华代表双方签署协议。</p>
<p>根据协议，双方将共建储能技术联合实验室，首批投入研发经费5000万元，重点攻关钠离子电池产业化技术。</p>
<p>签约仪式后，双方还共同为"研究生联合培养基地"揭牌，计划每年联合培养硕士研究生30名。</p>
</body></html>""",
    "nonnews_product.html": """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>XX牌空气炸锅 限时特惠</title></head>
<body>
<h1>XX牌空气炸锅 5L大容量 限时特惠</h1>
<p>原价599元，现价仅需299元！点击立即购买！</p>
<p>产品参数：容量5L，功率1500W，360度热风循环，智能触控面板，八种烹饪模式。</p>
<p>好评率99%，已售10万+件。七天无理由退货，一年质保。</p>
</body></html>""",
    "nonnews_tutorial.html": """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Python入门教程：列表推导式</title></head>
<body>
<h1>Python入门教程：五分钟学会列表推导式</h1>
<p>列表推导式是 Python 中创建列表的简洁语法。基本形式为 [表达式 for 变量 in 可迭代对象]。</p>
<p>例如，生成 1 到 10 的平方列表：squares = [x**2 for x in range(1, 11)]。</p>
<p>还可以加上条件过滤：[x for x in range(20) if x % 2 == 0] 得到 20 以内的偶数。</p>
<p>掌握列表推导式可以让代码更简洁，但过度嵌套会降低可读性，建议不超过两层。</p>
</body></html>""",
    "nonnews_navlist.html": """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>网站导航</title></head>
<body>
<ul>
<li><a href="/news">新闻中心</a></li>
<li><a href="/products">产品列表</a></li>
<li><a href="/about">关于我们</a></li>
<li><a href="/contact">联系方式</a></li>
</ul>
</body></html>""",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="samples_pool/meta")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, html in SAMPLES.items():
        (out / name).write_text(html, encoding="utf-8")
        print("written", out / name)


if __name__ == "__main__":
    main()
