import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from config.settings import settings
from utils.logger import logger


class ApprovalStatus(Enum):
    """承認ステータス"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPriority(Enum):
    """承認優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ApprovalRequest:
    """承認リクエストデータクラス"""
    request_id: str
    invoice_id: str
    project_id: str
    client_name: str
    project_name: str
    billing_amount: int
    pdf_path: str
    requestor: str
    approver: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    priority: ApprovalPriority = ApprovalPriority.NORMAL
    created_at: datetime = None
    due_date: datetime = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    slack_message_ts: Optional[str] = None
    slack_channel: Optional[str] = None
    comments: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.due_date is None:
            self.due_date = self.created_at + timedelta(days=3)
        if self.comments is None:
            self.comments = []


class ApprovalWorkflowManager:
    """承認ワークフロー管理クラス"""

    def __init__(self, db_path: str = "data/approval_workflow.db"):
        self.db_path = db_path
        self.db_dir = os.path.dirname(db_path)

        # データベースディレクトリの作成
        if self.db_dir and not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)

        self._init_database()

    def _init_database(self):
        """データベースの初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 承認リクエストテーブルの作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS approval_requests (
                        request_id TEXT PRIMARY KEY,
                        invoice_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        client_name TEXT NOT NULL,
                        project_name TEXT NOT NULL,
                        billing_amount INTEGER NOT NULL,
                        pdf_path TEXT NOT NULL,
                        requestor TEXT NOT NULL,
                        approver TEXT,
                        status TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        due_date TEXT NOT NULL,
                        approved_at TEXT,
                        rejected_at TEXT,
                        rejection_reason TEXT,
                        slack_message_ts TEXT,
                        slack_channel TEXT,
                        comments TEXT,
                        updated_at TEXT NOT NULL
                    )
                ''')

                # 承認履歴テーブルの作成
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS approval_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        details TEXT,
                        FOREIGN KEY (request_id) REFERENCES approval_requests (request_id)
                    )
                ''')

                # インデックスの作成
                cursor.execute(
                    'CREATE INDEX IF NOT EXISTS idx_status ON approval_requests (status)')
                cursor.execute(
                    'CREATE INDEX IF NOT EXISTS idx_due_date ON approval_requests (due_date)')
                cursor.execute(
                    'CREATE INDEX IF NOT EXISTS idx_project_id ON approval_requests (project_id)')

                conn.commit()
                logger.info("Approval workflow database initialized")

        except Exception as e:
            logger.error(
                f"Failed to initialize approval workflow database: {e}")
            raise

    def create_approval_request(
            self, approval_data: Dict[str, Any]) -> ApprovalRequest:
        """承認リクエストの作成"""
        try:
            # リクエストIDの生成
            request_id = f"APR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{approval_data['project_id']}"

            # ApprovalRequestオブジェクトの作成
            approval_request = ApprovalRequest(
                request_id=request_id,
                invoice_id=approval_data['invoice_id'],
                project_id=approval_data['project_id'],
                client_name=approval_data['client_name'],
                project_name=approval_data['project_name'],
                billing_amount=approval_data['billing_amount'],
                pdf_path=approval_data['pdf_path'],
                requestor=approval_data['requestor'],
                priority=ApprovalPriority(
                    approval_data.get(
                        'priority',
                        'normal')),
                due_date=datetime.fromisoformat(
                    approval_data['due_date']) if isinstance(
                    approval_data.get('due_date'),
                    str) else approval_data.get('due_date'))

            # データベースに保存
            self._save_approval_request(approval_request)

            # 履歴に記録
            self._add_approval_history(
                approval_request.request_id,
                "created",
                approval_request.requestor,
                "Approval request created")

            logger.info(f"Approval request created: {request_id}")
            return approval_request

        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            raise

    def _save_approval_request(self, approval_request: ApprovalRequest):
        """承認リクエストをデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    '''
                    INSERT OR REPLACE INTO approval_requests (
                        request_id, invoice_id, project_id, client_name, project_name,
                        billing_amount, pdf_path, requestor, approver, status, priority,
                        created_at, due_date, approved_at, rejected_at, rejection_reason,
                        slack_message_ts, slack_channel, comments, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                    (approval_request.request_id,
                     approval_request.invoice_id,
                     approval_request.project_id,
                     approval_request.client_name,
                     approval_request.project_name,
                     approval_request.billing_amount,
                     approval_request.pdf_path,
                     approval_request.requestor,
                     approval_request.approver,
                     approval_request.status.value,
                     approval_request.priority.value,
                     approval_request.created_at.isoformat(),
                     approval_request.due_date.isoformat(),
                     approval_request.approved_at.isoformat() if approval_request.approved_at else None,
                     approval_request.rejected_at.isoformat() if approval_request.rejected_at else None,
                     approval_request.rejection_reason,
                     approval_request.slack_message_ts,
                     approval_request.slack_channel,
                     json.dumps(
                         approval_request.comments),
                        datetime.now().isoformat()))

                conn.commit()

        except Exception as e:
            logger.error(f"Failed to save approval request: {e}")
            raise

    def get_approval_request(
            self,
            request_id: str) -> Optional[ApprovalRequest]:
        """承認リクエストの取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM approval_requests WHERE request_id = ?
                ''', (request_id,))

                row = cursor.fetchone()

                if row:
                    return self._row_to_approval_request(row)
                else:
                    return None

        except Exception as e:
            logger.error(f"Failed to get approval request: {e}")
            return None

    def _row_to_approval_request(self, row: Tuple) -> ApprovalRequest:
        """データベース行をApprovalRequestオブジェクトに変換"""
        return ApprovalRequest(
            request_id=row[0],
            invoice_id=row[1],
            project_id=row[2],
            client_name=row[3],
            project_name=row[4],
            billing_amount=row[5],
            pdf_path=row[6],
            requestor=row[7],
            approver=row[8],
            status=ApprovalStatus(row[9]),
            priority=ApprovalPriority(row[10]),
            created_at=datetime.fromisoformat(row[11]),
            due_date=datetime.fromisoformat(row[12]),
            approved_at=datetime.fromisoformat(row[13]) if row[13] else None,
            rejected_at=datetime.fromisoformat(row[14]) if row[14] else None,
            rejection_reason=row[15],
            slack_message_ts=row[16],
            slack_channel=row[17],
            comments=json.loads(row[18]) if row[18] else []
        )

    def update_approval_status(
            self,
            request_id: str,
            status: ApprovalStatus,
            approver: str,
            rejection_reason: Optional[str] = None) -> bool:
        """承認ステータスの更新"""
        try:
            approval_request = self.get_approval_request(request_id)
            if not approval_request:
                logger.error(f"Approval request not found: {request_id}")
                return False

            # ステータス更新
            approval_request.status = status
            approval_request.approver = approver

            if status == ApprovalStatus.APPROVED:
                approval_request.approved_at = datetime.now()
            elif status == ApprovalStatus.REJECTED:
                approval_request.rejected_at = datetime.now()
                approval_request.rejection_reason = rejection_reason

            # データベースに保存
            self._save_approval_request(approval_request)

            # 履歴に記録
            action = "approved" if status == ApprovalStatus.APPROVED else "rejected"
            details = f"Approval {action}" + (f": {rejection_reason}" if rejection_reason else "")
            self._add_approval_history(request_id, action, approver, details)

            logger.info(
                f"Approval status updated: {request_id} -> {status.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update approval status: {e}")
            return False

    def _add_approval_history(
            self,
            request_id: str,
            action: str,
            actor: str,
            details: str):
        """承認履歴の追加"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO approval_history (request_id, action, actor, timestamp, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (request_id, action, actor, datetime.now().isoformat(), details))

                conn.commit()

        except Exception as e:
            logger.error(f"Failed to add approval history: {e}")

    def get_pending_approvals(
            self,
            hours_until_due: Optional[int] = None) -> List[ApprovalRequest]:
        """保留中の承認リクエストを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if hours_until_due is not None:
                    # 指定時間以内に期限が来るリクエスト
                    due_threshold = datetime.now() + timedelta(hours=hours_until_due)
                    cursor.execute('''
                        SELECT * FROM approval_requests
                        WHERE status = ? AND due_date <= ?
                        ORDER BY priority DESC, due_date ASC
                    ''', (ApprovalStatus.PENDING.value, due_threshold.isoformat()))
                else:
                    # 全ての保留中リクエスト
                    cursor.execute('''
                        SELECT * FROM approval_requests
                        WHERE status = ?
                        ORDER BY priority DESC, due_date ASC
                    ''', (ApprovalStatus.PENDING.value,))

                rows = cursor.fetchall()
                return [self._row_to_approval_request(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []

    def get_expired_approvals(self) -> List[ApprovalRequest]:
        """期限切れの承認リクエストを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM approval_requests
                    WHERE status = ? AND due_date < ?
                    ORDER BY due_date ASC
                ''', (ApprovalStatus.PENDING.value, datetime.now().isoformat()))

                rows = cursor.fetchall()
                return [self._row_to_approval_request(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get expired approvals: {e}")
            return []

    def update_slack_message_info(
            self,
            request_id: str,
            message_ts: str,
            channel: str) -> bool:
        """Slackメッセージ情報の更新"""
        try:
            approval_request = self.get_approval_request(request_id)
            if not approval_request:
                return False

            approval_request.slack_message_ts = message_ts
            approval_request.slack_channel = channel

            self._save_approval_request(approval_request)
            return True

        except Exception as e:
            logger.error(f"Failed to update Slack message info: {e}")
            return False

    def add_comment(self, request_id: str, comment: str, author: str) -> bool:
        """コメントの追加"""
        try:
            approval_request = self.get_approval_request(request_id)
            if not approval_request:
                return False

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            formatted_comment = f"[{timestamp}] {author}: {comment}"
            approval_request.comments.append(formatted_comment)

            self._save_approval_request(approval_request)

            # 履歴に記録
            self._add_approval_history(
                request_id, "commented", author, f"Comment: {comment}")

            return True

        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return False

    def get_approval_statistics(self) -> Dict[str, Any]:
        """承認統計情報を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # ステータス別件数
                cursor.execute('''
                    SELECT status, COUNT(*) FROM approval_requests
                    GROUP BY status
                ''')
                status_counts = dict(cursor.fetchall())

                # 優先度別件数
                cursor.execute('''
                    SELECT priority, COUNT(*) FROM approval_requests
                    WHERE status = ?
                    GROUP BY priority
                ''', (ApprovalStatus.PENDING.value,))
                priority_counts = dict(cursor.fetchall())

                # 期限切れ件数
                cursor.execute('''
                    SELECT COUNT(*) FROM approval_requests
                    WHERE status = ? AND due_date < ?
                ''', (ApprovalStatus.PENDING.value, datetime.now().isoformat()))
                expired_count = cursor.fetchone()[0]

                return {
                    'total_requests': sum(
                        status_counts.values()),
                    'pending_requests': status_counts.get(
                        ApprovalStatus.PENDING.value,
                        0),
                    'approved_requests': status_counts.get(
                        ApprovalStatus.APPROVED.value,
                        0),
                    'rejected_requests': status_counts.get(
                        ApprovalStatus.REJECTED.value,
                        0),
                    'expired_requests': expired_count,
                    'priority_breakdown': priority_counts}

        except Exception as e:
            logger.error(f"Failed to get approval statistics: {e}")
            return {}


def main():
    """テスト用メイン処理"""
    # ワークフロー管理器の初期化
    workflow_manager = ApprovalWorkflowManager()

    # テスト用の承認リクエストデータ
    test_approval_data = {
        'invoice_id': 'INV-202506-001',
        'project_id': 'PRJ_0001',
        'client_name': '株式会社A',
        'project_name': 'システム開発プロジェクトA',
        'billing_amount': 1500000,
        'pdf_path': 'output/invoices/invoice_PRJ_0001_20250622_120526.pdf',
        'requestor': '田中太郎',
        'priority': 'normal',
        'due_date': datetime.now() + timedelta(days=2)
    }

    try:
        # 承認リクエストの作成
        approval_request = workflow_manager.create_approval_request(
            test_approval_data)
        print(f"✅ Approval request created: {approval_request.request_id}")

        # 保留中の承認リクエストを取得
        pending_approvals = workflow_manager.get_pending_approvals()
        print(f"📋 Pending approvals: {len(pending_approvals)}")

        # 統計情報の取得
        stats = workflow_manager.get_approval_statistics()
        print(f"📊 Approval statistics: {stats}")

    except Exception as e:
        logger.error(f"Approval workflow test failed: {e}")
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()
