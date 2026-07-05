# 📈 每日美股重磅新闻自动推送

每天北京时间 16:00 自动抓取美股市场重磅新闻，评分筛选 Top 10，发送精美 HTML 邮件到你的邮箱。

## ✨ 功能特点

- **多源聚合**：RSS 聚合主流财经媒体（Bloomberg, Reuters, CNBC, MarketWatch, Yahoo Finance, 财联社, 华尔街见闻等）
- **智能评分**：关键词加权（Fed/利率/通胀/财报/并购/指数异动等），自动去重，取 Top 10
- **精美邮件**：HTML + 纯文本双版本，含来源、时间、命中关键词、评分标签
- **全自动化**：GitHub Actions 定时运行，零服务器成本，失败自动创建 Issue 报警

## 🚀 5 分钟部署

### 1. Fork/Clone 本仓库

### 2. 配置 Secrets
在仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** 添加：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `SMTP_HOST` | SMTP 服务器 | `smtp-mail.outlook.com` (Outlook) / `smtp.gmail.com` (Gmail) |
| `SMTP_PORT` | 端口 | `587` |
| `SMTP_USER` | 发件邮箱 | `your_email@outlook.com` |
| `SMTP_PASS` | 邮箱密码/应用专用密码 | `xxxxxxxx` |
| `TO_EMAIL` | 收件邮箱 | `jqyangdaz@outlook.com` |

> **Gmail 用户**：必须开启「两步验证」→ 生成「应用专用密码」填入 `SMTP_PASS`  
> **Outlook 用户**：直接用登录密码即可，SMTP_HOST 用 `smtp-mail.outlook.com`

### 3. 启用 Actions
去 **Actions** 标签页点击 **I understand my workflows, go ahead and enable them**。

### 4. 手动测试
在 Actions 页面选中 `Daily US Stock Market News` → **Run workflow** → 绿色按钮运行一次，检查邮箱。

### 5. 定时自动运行
工作流已配置 `cron: "0 8 * * *"`（UTC 08:00 = 北京时间 16:00），每天自动执行。

## 📬 邮件效果预览

> **主题**：📈 美股重磅新闻 Top 10 — 2024-01-15
>
> 正文包含：标题链接、来源、北京时间、评分徽章（红≥6/橙3-5/蓝<3）、命中关键词

## ⚙️ 自定义关键词权重
编辑 `src/fetch_news.py` 顶部的 `KEYWORDS_HIGH` / `KEYWORDS_MED` 列表。

## 📦 本地调试
```bash
git clone https://github.com/jqyangDaz/us-stock-news-bot.git
cd us-stock-news-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export SMTP_HOST=... SMTP_PORT=... SMTP_USER=... SMTP_PASS=... TO_EMAIL=...
python src/fetch_news.py
```

## 🛠 故障排查
- **邮件收不到**：检查垃圾箱；确认 SMTP 配置正确
- **新闻重复/遗漏**：调整关键词权重；RSS 源在 `SOURCES` 列表增删
- **Actions 失败**：查看 Run logs；常见是 Secrets 未设置
- **时区不对**：工作流 cron 固定 UTC 08:00，如需改时间修改 `.github/workflows/daily-news.yml`

## 📄 License
MIT — 随意用、改、商用。# trigger workflow
