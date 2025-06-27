from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmailRecipient:
    email: str
    name: str
    company: str


class EmailRecipientManager:
    """
    メール送信先管理クラス
    - data/email_recipients.json から送信先情報を読み込む
    - プロジェクトIDごと、またはデフォルトの送信先を返す
    - CC/BCCリストも取得可能
    - 柔軟な設定（use_project_specific, fallback_to_default, include_cc, include_bcc）に対応
    """

    def __init__(self, config_path: str = 'data/email_recipients.json'):
        self.config_path = config_path
        self.data = self._load_config()
        self.settings = self.data.get('settings', {})

    def _load_config(self) -> Dict:
        if not os.path.exists(self.config_path):
            logger.error(f"Email recipient config not found: {self.config_path}")
            raise FileNotFoundError(
                f"Email recipient config not found: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_recipients(
            self,
            project_id: Optional[str] = None) -> List[EmailRecipient]:
        recipients = []
        if self.settings.get('use_project_specific', True) and project_id:
            project_map = self.data.get('project_specific_recipients', {})
            if project_id in project_map:
                recipients = [EmailRecipient(**r)
                              for r in project_map[project_id]]
        if not recipients and self.settings.get('fallback_to_default', True):
            recipients = [EmailRecipient(
                **r) for r in self.data.get('default_recipients', [])]
        return recipients

    def get_cc_recipients(self) -> List[EmailRecipient]:
        if self.settings.get('include_cc', True):
            return [EmailRecipient(**r)
                    for r in self.data.get('cc_recipients', [])]
        return []

    def get_bcc_recipients(self) -> List[EmailRecipient]:
        if self.settings.get('include_bcc', False):
            return [EmailRecipient(**r)
                    for r in self.data.get('bcc_recipients', [])]
        return []
