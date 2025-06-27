#!/usr/bin/env python3
"""
Gmail送信機能テストスクリプト
"""

import os
import sys
from datetime import datetime, timedelta
from src.email_utils.invoice_email_sender import GmailEmailSender, InvoiceEmailData, EmailRecipient
import pytest

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_gmail_authentication():
    """Gmail認証のテスト"""
    print("=== Gmail認証テスト ===")
    
    sender = GmailEmailSender()
    if sender.authenticate():
        print("✅ Gmail認証成功")
        return sender
    else:
        print("❌ Gmail認証失敗")
        return None

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_email_sending(sender: GmailEmailSender):
    """メール送信のテスト"""
    print("\n=== メール送信テスト ===")
    
    # テスト用の請求書データ
    email_data = sender.prepare_email_data(
        invoice_id="TEST_001",
        project_id="PRJ_TEST",
        client_name="テスト株式会社",
        project_name="Gmail送信テストプロジェクト",
        billing_amount=50000,
        billing_period="2025年6月",
        due_date=(datetime.now() + timedelta(days=30)).strftime("%Y年%m月%d日"),
        pdf_path="output/invoices/invoice_PRJ_0001_20250622_120526.pdf",
        custom_message="これはGmail送信機能のテストメールです。"
    )
    
    try:
        # メール送信
        success = sender.send_invoice_email(email_data)
        
        if success:
            print("✅ テストメール送信成功")
            
            # 統計情報の表示
            stats = sender.get_email_statistics()
            print(f"\n📊 送信統計:")
            print(f"  総送信数: {stats['total_sent']}")
            print(f"  成功: {stats['successful_sends']}")
            print(f"  失敗: {stats['failed_sends']}")
            print(f"  総受信者数: {stats['total_recipients']}")
            print(f"  総添付ファイル数: {stats['total_attachments']}")
        else:
            print("❌ テストメール送信失敗")
            
    except Exception as e:
        print(f"❌ メール送信エラー: {e}")

def test_email_data_preparation():
    """メールデータ準備のテスト（CIでも実行）"""
    print("=== メールデータ準備テスト ===")
    
    sender = GmailEmailSender()
    
    # テスト用の請求書データ
    email_data = sender.prepare_email_data(
        invoice_id="TEST_001",
        project_id="PRJ_0001",
        client_name="テスト株式会社",
        project_name="Gmail送信テストプロジェクト",
        billing_amount=50000,
        billing_period="2025年6月",
        due_date=(datetime.now() + timedelta(days=30)).strftime("%Y年%m月%d日"),
        pdf_path="output/invoices/invoice_PRJ_0001_test.pdf",
        custom_message="これはGmail送信機能のテストメールです。"
    )
    
    assert email_data.invoice_id == "TEST_001"
    assert email_data.project_id == "PRJ_0001"
    assert email_data.client_name == "テスト株式会社"
    assert email_data.billing_amount == 50000
    assert email_data.recipient is not None
    
    print("✅ メールデータ準備テスト成功")

def main():
    """メイン処理"""
    print("Gmail送信機能テスト")
    print("=" * 50)
    
    # Gmail認証テスト
    sender = test_gmail_authentication()
    
    if sender:
        # メール送信テスト
        test_email_sending(sender)
    else:
        print("認証に失敗したため、メール送信テストをスキップします。")

@pytest.fixture
def sender():
    return GmailEmailSender()

if __name__ == "__main__":
    main() 