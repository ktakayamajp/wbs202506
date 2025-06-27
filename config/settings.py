import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class Settings:
    # Slack
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")
    SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_DEFAULT_CHANNEL", "#general")
    SLACK_APPROVAL_CHANNEL = os.getenv("SLACK_APPROVAL_CHANNEL", "#invoice-approval")

    # Gmail API
    GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN", "")
    GMAIL_SENDER = os.getenv("GMAIL_SENDER", "kanji.takayama@gmail.com")

    # OpenRouter (OpenAI API)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

    # その他
    INVOICE_OUTPUT_DIR = os.getenv("INVOICE_OUTPUT_DIR", "./output/invoices")
    BANK_DATA_DIR = os.getenv("BANK_DATA_DIR", "./data/bank")

settings = Settings() 