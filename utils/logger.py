import logging
from logging.handlers import RotatingFileHandler
import json
import os
from datetime import datetime

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
MAX_BYTES = 1 * 1024 * 1024  # 1MB
BACKUP_COUNT = 3

os.makedirs(LOG_DIR, exist_ok=True)

class JsonLinesFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)

logger = logging.getLogger("wbs202506b")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
handler.setFormatter(JsonLinesFormatter())
logger.addHandler(handler)

# コンソールにも出力したい場合は以下を有効化
# console_handler = logging.StreamHandler()
# console_handler.setFormatter(JsonLinesFormatter())
# logger.addHandler(console_handler) 