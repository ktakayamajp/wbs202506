# 開発・運用フロー

## 1. 開発フロー

### タスク管理
- todo_r.mdでタスクを上から順に管理
- 1タスクずつ実装・検証・コミット
- ブロック時は[!]に変更し、相談

### 実装・テスト・コミット
- コード修正後、pytest等でテスト実行
- テスト成功後のみ[ ]→[x]に変更し、git commit
- コミットメッセージ例: `feat: ✅ <タスク内容>`

### レビュー・マージ
- 必要に応じてプルリクエスト作成・レビュー
- master/mainブランチへマージ

### CI/CD
- GitHub Actions等でpush/pull requestごとにpytest自動実行
- テスト失敗時は修正→再push

## 2. 運用フロー

### バッチ実行
- Web UI（web_entry.py）またはCLI（main_execution.py）でバッチ処理実行
- 実行後はlogs/app.logやoutput/配下で結果確認

### 障害対応
- エラー発生時はlogs/app.logやSlack通知を確認
- 必要に応じて再実行、データ修正、設定見直し

### データ・設定ファイル更新
- data/配下のCSVやjson、.env等を適宜更新
- 機密情報は.gitignoreで管理

### ログ・レポート確認
- logs/app.logやoutput/reports/配下のレポートを定期確認
- 問題発生時は関係者に連絡

## 入金マッチング処理フロー

### 1. 銀行データ前処理
- **入力**: `data/03_Bank_Data_Final.csv`
- **処理**: 銀行取引データの前処理・検証
- **出力**: `output/bank_processing/processed_bank_txn_*.csv`

### 2. AIによる入金マッチング
- **入力**: 
  - `output/ai_output/draft_invoice_202401.json` (請求書データ)
  - `data/03_Bank_Data_Final.csv` (入金データ)
- **処理**: AIによる請求書と入金のマッチング
- **出力**: `output/ai_output/match_suggestion_202401.json`

### 3. JSON→CSV変換処理 ⭐ **新規追加**
- **入力**: 
  - `output/ai_output/match_suggestion_202401.json` (AIマッチング結果)
  - `output/ai_output/draft_invoice_202401.json` (請求書データ)
- **処理**: 
  - JSONからCSV形式への変換
  - データ整合性チェック
  - エラーハンドリング
- **出力**: `output/ai_output/match_suggestion_202401.csv`

### 4. 入金マッチング適用
- **入力**: 
  - `output/ai_output/match_suggestion_202401.csv` (マッチング提案)
  - `output/bank_processing/processed_bank_txn_*.csv` (銀行データ)
  - `output/seed/invoice_seed_202401.csv` (請求書シード)
- **処理**: マッチング提案の適用・仕訳生成
- **出力**: `output/journal/journal_*.csv`

## データ変換詳細

### JSON→CSV変換マッピング
| JSON項目 | CSV項目 | 説明 |
|---------|---------|------|
| `invoice_id` | `project_id` | プロジェクトID |
| `payment_id` | `transaction_id` | 取引ID (TXN_{payment_id}_{invoice_id}形式) |
| `match_amount` | `amount`, `matched_amount` | マッチング金額 |
| `confidence_score` | `match_score` | 信頼度スコア |
| `match_type` | `comment` | マッチングタイプと信頼度 |
| 請求書データから取得 | `client_name` | 実際の会社名 |

### データ整合性チェック項目
1. **プロジェクトID整合性**: CSVと請求書データのプロジェクトID一致
2. **client_name検証**: Unknown値の検出と警告
3. **金額データ妥当性**: 0以下値の検出と修正
4. **信頼度スコア範囲**: 0-1の範囲チェック
5. **必須フィールド存在**: 全必須項目の存在確認

### エラーハンドリング
- **データ不整合時**: 自動修正機能でデフォルト値を設定
- **ファイル不存在時**: 適切なエラーメッセージとログ出力
- **JSON形式エラー時**: パース失敗時の処理
- **CSV保存失敗時**: ディレクトリ作成と権限チェック

## 品質保証

### 単体テスト
- **テストファイル**: `tests/test_convert_match_suggestion.py`
- **テストケース数**: 10個
- **カバレッジ**: 全主要機能をカバー
- **実行方法**: `python -m pytest tests/test_convert_match_suggestion.py -v`

### 統合テスト
- **実行方法**: `python src/main_execution.py --mode matching`
- **検証項目**: 
  - 3段階処理の正常実行
  - CSVファイルの正しい生成
  - 実際の会社名の含まれ方
  - データ形式の妥当性

## 運用上の注意点

### ファイル管理
- 古いテストデータファイルの整理が必要
- JSONとCSVファイルの同期確認
- バックアップファイルの管理

### ログ監視
- 変換処理の実行ログ確認
- エラー・警告メッセージの監視
- データ整合性チェック結果の確認

### パフォーマンス
- 大量データ処理時のメモリ使用量
- ファイルI/Oの最適化
- 処理時間の監視

---

（このドキュメントは2025年6月時点の運用ルールです。必要に応じて随時更新してください） 