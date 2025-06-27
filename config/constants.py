# アプリケーション定数定義

# ファイルパス
DEFAULT_INVOICE_TEMPLATE = "templates/invoice_template.html"
DEFAULT_CSS_FILE = "static/css/invoice_styles.css"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_LOG_DIR = "logs"

# ステータス定数
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_COMPLETED = "completed"

# ファイル名パターン
INVOICE_SEED_PATTERN = "invoice_seed_{yearmonth}.csv"
DRAFT_INVOICE_PATTERN = "draft_invoice_{yearmonth}.json"
BANK_DATA_PATTERN = "bank_{yearmonth}.csv"
MATCH_SUGGESTION_PATTERN = "match_suggestion_{yearmonth}.csv"
JOURNAL_PATTERN = "journal_{yearmonth}.csv"

# エラーメッセージ
ERROR_INVALID_DATA = "Invalid data format"
ERROR_FILE_NOT_FOUND = "File not found"
ERROR_API_FAILURE = "API request failed"

# 設定値
MAX_RETRY_COUNT = 3
REQUEST_TIMEOUT = 30
LOG_MAX_SIZE = 1024 * 1024  # 1MB
LOG_BACKUP_COUNT = 3

# 日付フォーマット
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
YEARMONTH_FORMAT = "%Y%m"

# データ検証・バリデーション用定数
AMOUNT_SMALL_MAX = 100000  # 金額カテゴリ: smallの上限
AMOUNT_MEDIUM_MAX = 500000  # 金額カテゴリ: mediumの上限
CONFIDENCE_THRESHOLD_DEFAULT = 0.8  # マッチング信頼度のデフォルト閾値
MATCH_SCORE_MIN = 0.0  # マッチングスコア最小値
MATCH_SCORE_MAX = 1.0  # マッチングスコア最大値
YEAR_MIN = 2020  # 年の下限
YEAR_MAX = 2030  # 年の上限
MONTH_MIN = 1  # 月の下限
MONTH_MAX = 12  # 月の上限
OUTLIER_STDDEV = 3  # 異常値判定の標準偏差倍率
INVOICE_MONTHLY_LIMIT = 20  # 1ヶ月あたりの請求書上限
DUE_DATE_OFFSET_DAYS = 30  # 請求書の支払期限日数
AMOUNT_TOLERANCE = 1  # 金額整合性判定の許容誤差 