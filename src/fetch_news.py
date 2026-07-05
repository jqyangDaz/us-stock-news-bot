#!/usr/bin/env python3
"""
Fetch top 10 market-moving news for US stocks.
Runs daily at 4 PM Beijing time (4 AM UTC / 12 AM ET).
"""
import os
import re
import json
import smtplib
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import List, Optional

# ---------- 配置 ----------
BEIJING_TZ = timezone(timedelta(hours=8))
KEYWORDS_HIGH = [
    # 宏观/货币政策
    "美联储", "联储", "Fed", "FOMC", "利率", "加息", "降息", "货币政策",
    "CPI", "PCE", "通胀", "非农", "就业", "失业率", "GDP", "零售销售",
    "鲍威尔", "Powell", "耶伦", "Yellen",
    # 地缘/大类资产
    "地缘", "中东", "俄乌", "贸易战", "关税", "制裁",
    "原油", "黄金", "美元指数", "美债", "国债收益率",
    # 重大财报/个股
    "财报", "业绩", "营收", "净利润", "EPS", "指引", "下调", "上调",
    "苹果", "微软", "英伟达", "特斯拉", "亚马逊", "Meta", "谷歌", "Alphabet",
    "伯克希尔", "巴菲特",
    # 系统性风险
    "银行危机", "信贷", "违约", "衰退", "硬着陆", "软着陆",
]
KEYWORDS_MED = [
    "标普", "纳斯达克", "道指", "期指", "VIX", "恐慌指数",
    "IPO", "回购", "分红", "拆股", "并购", "收购",
    "ETF", "期权", "做空", "做多", "机构", "对冲基金",
]

SOURCES = [
    # 中文财经（免费 RSS）
    ("财联社-美股", "https://www.cls.cn/rss/telegraph/us-stock.xml"),
    ("华尔街见闻-美股", "https://wallstreetcn.com/rss/us-stock"),
    ("新浪财经-美股", "https://finance.sina.com.cn/roll/index.d.html?cid=113366"),
    # 英文主流（免费 RSS）
    ("Reuters-Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters-Markets", "https://feeds.reuters.com/reuters/marketsNews"),
    ("Bloomberg-Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("CNBC-Top", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("MarketWatch-Top", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Yahoo-Finance", "https://finance.yahoo.com/news/rssindex"),
    ("SeekingAlpha-Market", "https://seekingalpha.com/market_currents.xml"),
]

MAX_ITEMS_PER_SOURCE = 30
TOP_N = 10


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    published: datetime
    score: int = 0
    reason: str = ""


def score_title(title: str) -> tuple[int, str]:
    """返回 (分数, 命中理由)"""
    title_l = title.lower()
    hits = []
    score = 0
    for kw in KEYWORDS_HIGH:
        if kw.lower() in title_l:
            score += 3
            hits.append(kw)
    for kw in KEYWORDS_MED:
        if kw.lower() in title_l:
            score += 1
            hits.append(kw)
    return score, ", ".join(hits)


def fetch_rss(url: str, source: str, limit: int) -> List[NewsItem]:
    """抓取单个 RSS 源"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"[WARN] {source} fetch failed: {e}")
        return []

    items = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue
        # 解析时间
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if pub:
            dt = datetime(*pub[:6], tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        items.append(NewsItem(title, link, source, dt))
    return items


def fetch_all() -> List[NewsItem]:
    all_items = []
    for name, url in SOURCES:
        items = fetch_rss(url, name, MAX_ITEMS_PER_SOURCE)
        all_items.extend(items)
        print(f"[INFO] {name}: {len(items)} items")
    return all_items


def deduplicate(items: List[NewsItem]) -> List[NewsItem]:
    """按标题相似度去重（简单版）"""
    seen = set()
    uniq = []
    for it in items:
        key = re.sub(r"[^\w一-鿿]+", "", it.title.lower())[:60]
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    return uniq


def rank_and_pick(items: List[NewsItem], top_n: int) -> List[NewsItem]:
    for it in items:
        it.score, it.reason = score_title(it.title)
    # 分数降序、时间降序
    items.sort(key=lambda x: (x.score, x.published), reverse=True)
    return items[:top_n]


def format_email(items: List[NewsItem], date_str: str) -> tuple[str, str]:
    """生成纯文本 + HTML 邮件"""
    lines = [f"📈  美股市场重磅新闻 Top {len(items)}  —  {date_str} (北京时间 16:00 自动发送)\n"]
    html = [
        "<html><body style='font-family: -apple-system, BlinkMacSystemFont, "
        "'Segoe UI', Roboto, sans-serif; line-height:1.6; color:#1a1a2e; "
        "max-width:720px; margin:auto; padding:20px;'>",
        f"<h2 style='color:#0f172a; border-bottom:2px solid #3b82f6; "
        f"padding-bottom:8px;'>📈  美股市场重磅新闻 Top {len(items)}</h2>",
        f"<p style='color:#64748b;'>北京时间 {date_str} 16:00 自动采集·"
        f"来源：财联社/华尔街见闻/Reuters/Bloomberg/CNBC/MarketWatch/Yahoo/SeekingAlpha</p>",
        "<ol style='padding-left:1.2rem;'>",
    ]
    for i, it in enumerate(items, 1):
        score_tag = ""
        if it.score > 0:
            score_tag = f" <span style='background:#3b82f6;color:#fff;padding:2px 6px;border-radius:4px;font-size:0.75rem;margin-left:8px;'>+{it.score}</span>"
            if it.reason:
                score_tag += f" <span style='color:#64748b;font-size:0.8rem;'>({it.reason})</span>"
        lines.append(f"{i}. {it.title} ({it.source})")
        if it.reason:
            lines.append(f"   ↳ 命中: {it.reason}")
        lines.append(f"   {it.link}\n")

        html.append(
            f"<li style='margin-bottom:16px;'>"
            f"<a href='{it.link}' style='color:#1e293b;text-decoration:none;font-weight:500;' target='_blank'>{it.title}</a>"
            f"<span style='color:#64748b;font-size:0.85rem;margin-left:8px;'>({it.source})</span>"
            f"{score_tag}"
            f"</li>"
        )
    lines.append("\n—— 自动生成 by GitHub Actions · 仅供参考，不构成投资建议")
    html.append("</ol>")
    html.append("<hr style='border:none;border-top:1px solid #e2e8f0;margin:24px 0;'/>")
    html.append("<p style='color:#94a3b8;font-size:0.85rem;text-align:center;'>"
                "自动生成 by GitHub Actions · 仅供参考，不构成投资建议</p>")
    html.append("</body></html>")
    return "\n".join(lines), "\n".join(html)


def send_email(text_body: str, html_body: str, date_str: str) -> bool:
    """发送邮件"""
    smtp_host = os.getenv("SMTP_HOST", "smtp-mail.outlook.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email = os.getenv("TO_EMAIL")

    if not all([smtp_user, smtp_pass, to_email]):
        print("[ERROR] Missing email env vars")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 美股重磅新闻 Top {len(text_body.split(chr(10))) - 3} — {date_str}"
    msg["From"] = smtp_user
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[INFO] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Send email failed: {e}")
        return False


def main():
    now_beijing = datetime.now(BEIJING_TZ)
    date_str = now_beijing.strftime("%Y-%m-%d")

    print(f"[INFO] Fetching news for {date_str}...")
    items = fetch_all()
    print(f"[INFO] Total fetched: {len(items)}")

    items = deduplicate(items)
    print(f"[INFO] After dedup: {len(items)}")

    top_items = rank_and_pick(items, TOP_N)
    print(f"[INFO] Top {TOP_N} selected:")
    for i, it in enumerate(top_items, 1):
        print(f"  {i}. [{it.score}] {it.title[:60]}... ({it.source})")

    text_body, html_body = format_email(top_items, date_str)
    ok = send_email(text_body, html_body, date_str)
    exit(0 if ok else 1)


if __name__ == "__main__":
    main()