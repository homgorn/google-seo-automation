# Google SEO Automation

Google Analytics 4、Google Tag Manager、Google Search Console、
Google Ads 和 AI 回答 (AI Overviews / AEO) 的自动化，基于**可自行更新的
内部知识库**，该知识库从官方的机器可读 Discovery 文档构建而成。

> 状态：知识库基础设施已运行。GA4/GTM/GSC/Ads 集成已实现并验证；
> 实时 API 调用需要凭据（参见 `.env.example`）。

---

## 已运行功能

- 从 7 个 Google Discovery 文档中自动提取 **312 个端点**
- **全文搜索**（SQLite FTS5，无外部依赖）
- 通过 SHA256 **变更检测** + `change_log` 审计追踪
- 14 天阈值 **新鲜度检查** + cron 调度
- 覆盖开发期间发现的 4 个 bug 的 **16 个回归测试**
- 具有明确输入/输出契约的 **7 个代理角色**
- **11 个功能中的 8 个**已验证 (PASS)；3 个仅因外部凭据而阻塞

## 快速开始

```bash
cd project

# 1. 检查环境并安装依赖
./init.sh

# 2. 创建/更新数据库架构（幂等，含迁移）
python scripts/init_db.py

# 3. 从 Google 获取最新文档
python scripts/sync_wiki.py --full

# 4. 验证所有内容都是最新的
python scripts/sync_wiki.py --check-freshness
```

## API 来源（2026-10-12 测量）

| 来源 | Discovery 文档 | 端点 |
|------|---------------|------|
| Google Analytics Admin API v1alpha | `analyticsadmin.googleapis.com` | 166 |
| Google Tag Manager API v2 | `tagmanager.googleapis.com` | 106 |
| Google Business Profile API v1 | `mybusinessbusinessinformation.googleapis.com` | 15 |
| Google Analytics Data API v1beta | `analyticsdata.googleapis.com` | 11 |
| Google Search Console API v1 | `searchconsole.googleapis.com` | 11 |
| Google Indexing API v3 | `indexing.googleapis.com` | 2 |
| PageSpeed Insights API v5 | `pagespeedonline.googleapis.com` | 1 |
| Google Merchant API v1 | `merchantapi.googleapis.com` | 0 (无方法) |
| **总计** | | **312** |

## 结构

完整项目结构请参见 [README.md](README.md)（英文版）。

## 安全

- `.env` 在 `.gitignore` 中；模板为 `.env.example`
- 密钥仅来自环境变量
- 默认 dry-run 模式（`ALLOW_MUTATIONS=0`）
- 数据库是缓存 — 从源重新生成

## 文档

- [架构](project/docs/architecture.md)
- [变更日志](project/docs/progress.md)
- [API 参考](project/wiki/api-reference.md)
- [Runbooks](project/docs/runbooks/)

## 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)