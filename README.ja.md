# Google SEO Automation

Google Analytics 4、Google Tag Manager、Google Search Console、
Google Ads および AI 回答 (AI Overviews / AEO) の自動化。公式の
機械可読な Discovery ドキュメントから構築された **自己更新型の内部
ナレッジベース** の上に構築されています。

> 状態: ナレッジベースのインフラは稼働中。GA4/GTM/GSC/Ads の
> 統合は実装・検証済み。ライブ API 呼び出しには認証情報が必要
> (`.env.example` を参照)。

---

## 動作するもの

- **312 エンドポイント**を 7 つの Google Discovery ドキュメントから自動抽出
- **全文検索** (SQLite FTS5, 外部依存なし)
- SHA256 による **変更検出** + `change_log` 監査証跡
- 14 日の閾値と cron スケジュールによる **鮮度チェック**
- 開発中に発見された 4 つのバグをカバーする **16 件の回帰テスト**
- 明示的な入出力契約を持つ **7 つのエージェントロール**
- **11 機能のうち 8 つ**が検証済み (PASS)；3 つは外部認証情報のみでブロック

## クイックスタート

```bash
cd project

# 1. 環境チェックと依存関係のインストール
./init.sh

# 2. DB スキーマの作成 / 更新 (冪等、マイグレーション付き)
python scripts/init_db.py

# 3. Google から最新ドキュメントを取得
python scripts/sync_wiki.py --full

# 4. すべてが最新であることを確認
python scripts/sync_wiki.py --check-freshness
```

## API ソース (2026-10-12 測定)

| ソース | Discovery ドキュメント | エンドポイント |
|--------|----------------------|---------------|
| Google Analytics Admin API v1alpha | `analyticsadmin.googleapis.com` | 166 |
| Google Tag Manager API v2 | `tagmanager.googleapis.com` | 106 |
| Google Business Profile API v1 | `mybusinessbusinessinformation.googleapis.com` | 15 |
| Google Analytics Data API v1beta | `analyticsdata.googleapis.com` | 11 |
| Google Search Console API v1 | `searchconsole.googleapis.com` | 11 |
| Google Indexing API v3 | `indexing.googleapis.com` | 2 |
| PageSpeed Insights API v5 | `pagespeedonline.googleapis.com` | 1 |
| Google Merchant API v1 | `merchantapi.googleapis.com` | 0 (メソッドなし) |
| **合計** | | **312** |

## 構造

完全なプロジェクト構造は [README.md](README.md) (英語) を参照してください。

## セキュリティ

- `.env` は `.gitignore` に含まれます；テンプレートは `.env.example`
- シークレットは環境変数からのみ取得
- ミューテーションはデフォルトで dry-run (`ALLOW_MUTATIONS=0`)
- データベースはキャッシュ — ソースから再生成

## ドキュメント

- [アーキテクチャ](project/docs/architecture.md)
- [変更ログ](project/docs/progress.md)
- [API リファレンス](project/wiki/api-reference.md)
- [Runbooks](project/docs/runbooks/)

## 貢献

[CONTRIBUTING.md](CONTRIBUTING.md) を参照。

## ライセンス

[MIT](LICENSE)