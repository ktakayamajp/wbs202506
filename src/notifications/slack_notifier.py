import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from config.settings import settings
from utils.logger import logger


@dataclass
class SlackMessage:
    """Slackメッセージデータクラス"""
    channel: str
    text: str
    blocks: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    thread_ts: Optional[str] = None


@dataclass
class InvoiceApprovalRequest:
    """請求書承認依頼データクラス"""
    invoice_id: str
    project_id: str
    client_name: str
    project_name: str
    billing_amount: int
    pdf_path: str
    requestor: str
    due_date: datetime
    priority: str = "normal"  # low, normal, high, urgent


class SlackNotifier:
    """Slack通知クラス"""

    def __init__(
            self,
            webhook_url: Optional[str] = None,
            bot_token: Optional[str] = None):
        self.webhook_url = webhook_url or settings.SLACK_WEBHOOK_URL
        self.bot_token = bot_token or settings.SLACK_BOT_TOKEN
        self.default_channel = settings.SLACK_DEFAULT_CHANNEL
        self.approval_channel = settings.SLACK_APPROVAL_CHANNEL

        # 通知統計
        self.notification_stats = {
            'total_sent': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'approval_requests': 0,
            'reminders_sent': 0
        }

    def _send_webhook_message(self, message: SlackMessage) -> bool:
        """Webhookを使用してメッセージを送信"""
        try:
            payload = {
                'channel': message.channel,
                'text': message.text
            }

            if message.blocks:
                payload['blocks'] = message.blocks

            if message.attachments:
                payload['attachments'] = message.attachments

            if message.thread_ts:
                payload['thread_ts'] = message.thread_ts

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Slack webhook message sent successfully to {self.webhook_url}")
                return True
            else:
                logger.error(
                    f"Slack webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Slack webhook message: {e}")
            return False

    def _send_api_message(self, message: SlackMessage) -> bool:
        """Slack APIを使用してメッセージを送信"""
        try:
            headers = {
                'Authorization': f'Bearer {self.bot_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'channel': message.channel,
                'text': message.text
            }

            if message.blocks:
                payload['blocks'] = message.blocks

            if message.attachments:
                payload['attachments'] = message.attachments

            if message.thread_ts:
                payload['thread_ts'] = message.thread_ts

            response = requests.post(
                'https://slack.com/api/chat.postMessage',
                headers=headers,
                json=payload,
                timeout=30
            )

            result = response.json()

            if result.get('ok'):
                logger.info(f"Slack API message sent successfully to {self.webhook_url}")
                return True
            else:
                logger.error(f"Slack API failed: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Slack API message: {e}")
            return False

    def send_message(self, message: SlackMessage) -> bool:
        """メッセージを送信（Webhook優先、APIフォールバック）"""
        self.notification_stats['total_sent'] += 1

        # Webhookを優先して試行
        if self.webhook_url:
            if self._send_webhook_message(message):
                self.notification_stats['successful_sends'] += 1
                return True

        # APIフォールバック
        if self.bot_token:
            if self._send_api_message(message):
                self.notification_stats['successful_sends'] += 1
                return True

        self.notification_stats['failed_sends'] += 1
        logger.error("Both webhook and API methods failed")
        return False

    def create_invoice_approval_message(
            self, approval_request: InvoiceApprovalRequest) -> SlackMessage:
        """請求書承認依頼メッセージの作成"""
        # 優先度に応じた色とアイコン
        priority_colors = {
            'low': '#36a64f',
            'normal': '#ff9900',
            'high': '#ff6b6b',
            'urgent': '#e74c3c'
        }

        priority_icons = {
            'low': '🟢',
            'normal': '🟡',
            'high': '🟠',
            'urgent': '🔴'
        }

        color = priority_colors.get(approval_request.priority, '#ff9900')
        icon = priority_icons.get(approval_request.priority, '🟡')

        # 承認期限の計算
        time_until_due = approval_request.due_date - datetime.now()
        if time_until_due.total_seconds() > 0:
            due_text = f"承認期限: {approval_request.due_date.strftime('%m/%d %H:%M')} (あと{time_until_due.days}日)"
        else:
            due_text = f"承認期限: {approval_request.due_date.strftime('%m/%d %H:%M')} (期限切れ)"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{icon} 請求書承認依頼",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*プロジェクトID:*\n{approval_request.project_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*請求書ID:*\n{approval_request.invoice_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*クライアント:*\n{approval_request.client_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*プロジェクト名:*\n{approval_request.project_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*請求金額:*\n¥{approval_request.billing_amount:,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*申請者:*\n{approval_request.requestor}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{due_text}*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ 承認",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": f"approve_{approval_request.invoice_id}",
                        "action_id": "approve_invoice"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ 却下",
                            "emoji": True
                        },
                        "style": "danger",
                        "value": f"reject_{approval_request.invoice_id}",
                        "action_id": "reject_invoice"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📝 コメント追加",
                            "emoji": True
                        },
                        "value": f"comment_{approval_request.invoice_id}",
                        "action_id": "add_comment"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"承認期限: {approval_request.due_date.strftime('%Y年%m月%d日 %H:%M')}"
                    }
                ]
            }
        ]

        # 添付ファイルがある場合
        attachments = []
        if approval_request.pdf_path and os.path.exists(
                approval_request.pdf_path):
            attachments.append({
                "color": color,
                "title": "📄 請求書PDF",
                "title_link": f"file://{os.path.abspath(approval_request.pdf_path)}",
                "text": "請求書の詳細を確認してください",
                "footer": "PDFファイル",
                "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
            })

        return SlackMessage(
            channel=self.approval_channel, text=f"請求書承認依頼: {approval_request.project_name} (¥{approval_request.billing_amount:,})", blocks=blocks, attachments=attachments)

    def send_invoice_approval_request(
            self, approval_request: InvoiceApprovalRequest) -> bool:
        """請求書承認依頼を送信"""
        try:
            message = self.create_invoice_approval_message(approval_request)
            success = self.send_message(message)

            if success:
                self.notification_stats['approval_requests'] += 1
                logger.info(f"Invoice approval request sent for {approval_request.invoice_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to send invoice approval request: {e}")
            return False

    def send_approval_result_notification(
            self,
            approval_request: InvoiceApprovalRequest,
            status: str,
            approver: str,
            rejection_reason: Optional[str] = None) -> bool:
        """承認結果通知の送信"""
        try:
            if status == "approved":
                # 承認通知
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ 請求書承認完了",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*プロジェクト:*\n{approval_request.project_name}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*承認者:*\n{approver}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*承認日時:*\n{datetime.now().strftime('%Y年%m月%d日 %H:%M')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*請求金額:*\n¥{approval_request.billing_amount:,}"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "承認が完了しました。請求書のメール送信を開始します。"
                            }
                        ]
                    }
                ]

                message = SlackMessage(
                    channel=self.approval_channel,
                    text=f"✅ 請求書承認完了: {approval_request.project_name}",
                    blocks=blocks
                )

            else:
                # 却下通知
                blocks = [
                    {
                        "type": "header", "text": {
                            "type": "plain_text", "text": "❌ 請求書却下", "emoji": True}}, {
                        "type": "section", "fields": [
                            {
                                "type": "mrkdwn", "text": f"*プロジェクト:*\n{approval_request.project_name}"}, {
                                "type": "mrkdwn", "text": f"*却下者:*\n{approver}"}, {
                                    "type": "mrkdwn", "text": f"*却下日時:*\n{datetime.now().strftime('%Y年%m月%d日 %H:%M')}"}, {
                                            "type": "mrkdwn", "text": f"*請求金額:*\n¥{approval_request.billing_amount:,}"}]}]

                if rejection_reason:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*却下理由:*\n{rejection_reason}"
                        }
                    })

                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "却下されました。申請者に連絡して修正をお願いします。"
                        }
                    ]
                })

                message = SlackMessage(
                    channel=self.approval_channel,
                    text=f"❌ 請求書却下: {approval_request.project_name}",
                    blocks=blocks
                )

            success = self.send_message(message)
            if success:
                logger.info(f"Approval result notification sent: {status}")
            return success

        except Exception as e:
            logger.error(f"Failed to send approval result notification: {e}")
            return False

    def send_approval_reminder(
            self,
            approval_request: InvoiceApprovalRequest,
            hours_remaining: int) -> bool:
        """承認リマインダーの送信"""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⏰ 承認期限リマインダー",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{approval_request.project_name}* の請求書承認がまだ完了していません。"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*残り時間:*\n{hours_remaining}時間"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*請求金額:*\n¥{approval_request.billing_amount:,}"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "早めの承認をお願いします。"
                        }
                    ]
                }
            ]

            message = SlackMessage(
                channel=self.approval_channel,
                text=f"⏰ 承認期限リマインダー: {approval_request.project_name}",
                blocks=blocks
            )

            success = self.send_message(message)
            if success:
                self.notification_stats['reminders_sent'] += 1
                logger.info(
                    f"Approval reminder sent for {approval_request.project_name}")
            return success

        except Exception as e:
            logger.error(f"Failed to send approval reminder: {e}")
            return False

    def send_batch_completion_notification(
            self, batch_info: Dict[str, Any]) -> bool:
        """バッチ処理完了通知を送信"""
        try:
            success_count = batch_info.get('successful_generations', 0)
            total_count = batch_info.get('total_invoices', 0)
            failed_count = batch_info.get('failed_generations', 0)

            # 成功率の計算
            success_rate = (
                success_count /
                total_count *
                100) if total_count > 0 else 0

            # 色の決定
            if success_rate >= 90:
                color = "good"
                icon = "✅"
            elif success_rate >= 70:
                color = "warning"
                icon = "⚠️"
            else:
                color = "danger"
                icon = "❌"

            text = f"{icon} 請求書生成バッチ処理完了\n"
            text += f"成功: {success_count}/{total_count} ({success_rate:.1f}%)\n"
            if failed_count > 0:
                text += f"失敗: {failed_count}件"

            message = SlackMessage(
                channel=self.default_channel,
                text=text
            )

            success = self.send_message(message)

            if success:
                logger.info(
                    f"Batch completion notification sent: {success_count}/{total_count} successful")

            return success

        except Exception as e:
            logger.error(f"Failed to send batch completion notification: {e}")
            return False

    def send_error_notification(self, error_info: Dict[str, Any]) -> bool:
        """エラー通知を送信"""
        try:
            error_type = error_info.get('type', 'Unknown')
            error_message = error_info.get('message', 'No message')
            timestamp = error_info.get(
                'timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            text = f"🚨 システムエラー発生\n"
            text += f"タイプ: {error_type}\n"
            text += f"メッセージ: {error_message}\n"
            text += f"時刻: {timestamp}"

            message = SlackMessage(
                channel=self.default_channel,
                text=text
            )

            success = self.send_message(message)

            if success:
                logger.info(f"Error notification sent: {error_type}")

            return success

        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            return False

    def get_notification_stats(self) -> Dict[str, Any]:
        """通知統計情報を取得"""
        return {
            'total_sent': self.notification_stats['total_sent'],
            'successful_sends': self.notification_stats['successful_sends'],
            'failed_sends': self.notification_stats['failed_sends'],
            'success_rate': (
                self.notification_stats['successful_sends'] /
                self.notification_stats['total_sent'] *
                100) if self.notification_stats['total_sent'] > 0 else 0,
            'approval_requests': self.notification_stats['approval_requests'],
            'reminders_sent': self.notification_stats['reminders_sent']}


def main():
    """テスト用メイン処理"""
    # テスト用の承認依頼データ
    test_approval = InvoiceApprovalRequest(
        invoice_id="INV-202506-001",
        project_id="PRJ_0001",
        client_name="株式会社A",
        project_name="システム開発プロジェクトA",
        billing_amount=1500000,
        pdf_path="output/invoices/invoice_PRJ_0001_20250622_120526.pdf",
        requestor="田中太郎",
        due_date=datetime.now() + timedelta(days=2),
        priority="normal"
    )

    # Slack通知器の初期化
    notifier = SlackNotifier()

    try:
        # 承認依頼の送信テスト
        success = notifier.send_invoice_approval_request(test_approval)

        if success:
            print("✅ Invoice approval request sent successfully")
        else:
            print("❌ Failed to send invoice approval request")

        # 統計情報の表示
        stats = notifier.get_notification_stats()
        print(f"📊 Notification stats: {stats}")

    except Exception as e:
        logger.error(f"Slack notification test failed: {e}")
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()
