#!/usr/bin/env python3
"""
Slack通知機能テストスクリプト
"""

import os
import sys
from datetime import datetime, timedelta
from src.notifications.slack_notifier import SlackNotifier, InvoiceApprovalRequest, SlackMessage
import pytest

def test_slack_configuration():
    """Slack設定の確認"""
    print("=== Slack設定確認 ===")
    
    from config.settings import settings
    
    print(f"SLACK_BOT_TOKEN: {'設定済み' if settings.SLACK_BOT_TOKEN else '未設定'}")
    print(f"SLACK_WEBHOOK_URL: {'設定済み' if settings.SLACK_WEBHOOK_URL else '未設定'}")
    print(f"SLACK_CHANNEL_ID: {'設定済み' if settings.SLACK_CHANNEL_ID else '未設定'}")
    print(f"SLACK_DEFAULT_CHANNEL: {settings.SLACK_DEFAULT_CHANNEL}")
    print(f"SLACK_APPROVAL_CHANNEL: {settings.SLACK_APPROVAL_CHANNEL}")
    
    return bool(settings.SLACK_BOT_TOKEN or settings.SLACK_WEBHOOK_URL)

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_simple_message(slack_notifier: SlackNotifier):
    """簡単なメッセージ送信テスト"""
    print("\n=== 簡単なメッセージ送信テスト ===")
    
    message = SlackMessage(
        channel=slack_notifier.default_channel,
        text="🧪 これはSlack通知機能のテストメッセージです。",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🧪 *Slack通知機能テスト*\n\nこれは請求書自動化システムのSlack通知機能のテストです。"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*テスト日時:*\n" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*ステータス:*\n✅ 正常動作"
                    }
                ]
            }
        ]
    )
    
    success = slack_notifier.send_message(message)
    
    if success:
        print("✅ 簡単なメッセージ送信成功")
    else:
        print("❌ 簡単なメッセージ送信失敗")
    
    return success

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_invoice_approval_request(slack_notifier: SlackNotifier):
    """請求書承認依頼テスト"""
    print("\n=== 請求書承認依頼テスト ===")
    
    approval_request = InvoiceApprovalRequest(
        invoice_id="INV_20250628_001",
        project_id="PRJ_0001",
        client_name="テスト株式会社",
        project_name="Slack通知機能テストプロジェクト",
        billing_amount=150000,
        pdf_path="output/invoices/invoice_PRJ_0001_20250622_120526.pdf",
        requestor="高山 完治",
        due_date=datetime.now() + timedelta(days=2),
        priority="normal"
    )
    
    success = slack_notifier.send_invoice_approval_request(approval_request)
    
    if success:
        print("✅ 請求書承認依頼送信成功")
    else:
        print("❌ 請求書承認依頼送信失敗")
    
    return success

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_error_notification(slack_notifier: SlackNotifier):
    """エラー通知テスト"""
    print("\n=== エラー通知テスト ===")
    
    error_info = {
        'error_type': 'TestError',
        'error_message': 'これはテスト用のエラー通知です',
        'timestamp': datetime.now().isoformat(),
        'module': 'test_slack_notifier',
        'severity': 'warning'
    }
    
    success = slack_notifier.send_error_notification(error_info)
    
    if success:
        print("✅ エラー通知送信成功")
    else:
        print("❌ エラー通知送信失敗")
    
    return success

def test_message_creation():
    """メッセージ作成のテスト（CIでも実行）"""
    print("=== メッセージ作成テスト ===")
    
    slack_notifier = SlackNotifier()
    
    # 承認依頼データの作成
    approval_request = InvoiceApprovalRequest(
        invoice_id="INV_TEST_001",
        project_id="PRJ_0001",
        client_name="テスト株式会社",
        project_name="テストプロジェクト",
        billing_amount=100000,
        pdf_path="output/invoices/invoice_PRJ_0001_test.pdf",
        requestor="テスト太郎",
        due_date=datetime.now() + timedelta(days=2),
        priority="normal"
    )
    
    # メッセージの作成
    message = slack_notifier.create_invoice_approval_message(approval_request)
    
    assert message.channel == slack_notifier.approval_channel
    assert "請求書承認依頼" in message.text
    assert approval_request.invoice_id in message.text
    assert message.blocks is not None
    
    print("✅ メッセージ作成テスト成功")

@pytest.fixture
def slack_notifier():
    return SlackNotifier()

def main():
    """メイン処理"""
    print("Slack通知機能テスト")
    print("=" * 50)
    
    # Slack設定確認
    if not test_slack_configuration():
        print("\n❌ Slack設定が不完全です。")
        print("以下の設定が必要です：")
        print("1. SLACK_BOT_TOKEN または SLACK_WEBHOOK_URL")
        print("2. SLACK_CHANNEL_ID（オプション）")
        print("\n.envファイルに設定を追加してください。")
        return
    
    # Slack通知クラスの初期化
    slack_notifier = SlackNotifier()
    
    # テスト実行
    test_results = []
    
    test_results.append(test_simple_message(slack_notifier))
    test_results.append(test_invoice_approval_request(slack_notifier))
    test_results.append(test_error_notification(slack_notifier))
    
    # 結果表示
    print("\n=== テスト結果 ===")
    successful_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f"成功: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 すべてのテストが成功しました！")
    else:
        print("⚠️ 一部のテストが失敗しました。")
    
    # 統計情報の表示
    stats = slack_notifier.get_notification_stats()
    print(f"\n📊 通知統計:")
    print(f"  総送信数: {stats['total_sent']}")
    print(f"  成功: {stats['successful_sends']}")
    print(f"  失敗: {stats['failed_sends']}")
    print(f"  承認依頼: {stats['approval_requests']}")
    print(f"  リマインダー: {stats['reminders_sent']}")

if __name__ == "__main__":
    main() 