#!/usr/bin/env python3
"""
承認ワークフロー統合テストスクリプト
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytest

# 各モジュールのインポート
from src.notifications.approval_workflow import ApprovalWorkflowManager, ApprovalStatus, ApprovalPriority
from src.notifications.slack_notifier import SlackNotifier, InvoiceApprovalRequest
from src.email_utils.invoice_email_sender import GmailEmailSender
from src.pdf_generation.build_invoice_pdf import InvoicePDFGenerator
from utils.logger import logger

class ApprovalWorkflowTest:
    """承認ワークフロー統合テストクラス"""
    
    def __init__(self):
        self.test_results = {
            'workflow_creation': False,
            'slack_notification': False,
            'approval_process': False,
            'email_sending': False
        }
        self.generated_files = []
        self.test_data = {}
        self.workflow_manager = ApprovalWorkflowManager()
        self.slack_notifier = SlackNotifier()
    
    def setup_test_data(self):
        """テストデータの準備"""
        print("=== テストデータ準備 ===")
        
        # テスト用の請求書データ
        self.test_data = {
            'invoice_id': f"INV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'project_id': 'PRJ_APPROVAL_TEST',
            'client_name': '承認テスト株式会社',
            'project_name': '承認ワークフローテストプロジェクト',
            'billing_amount': 300000,
            'billing_period': '2025年6月',
            'due_date': (datetime.now() + timedelta(days=2)).strftime('%Y年%m月%d日'),
            'requestor': '高山 完治',
            'approver': '承認者 太郎',
            'recipient_email': 'kanji.takayama@gmail.com',
            'recipient_name': '高山 完治',
            'recipient_company': '承認テスト株式会社'
        }
        
        print(f"✅ テストデータ準備完了")
        print(f"   請求書ID: {self.test_data['invoice_id']}")
        print(f"   プロジェクト: {self.test_data['project_name']}")
        print(f"   請求金額: ¥{self.test_data['billing_amount']:,}")
        print(f"   承認者: {self.test_data['approver']}")
        
        return True
    
    def test_workflow_creation(self):
        """承認ワークフロー作成テスト"""
        print("\n=== 承認ワークフロー作成テスト ===")
        
        try:
            # PDF生成
            pdf_generator = InvoicePDFGenerator()
            company_info = {
                'name': '承認テスト株式会社',
                'address': '東京都渋谷区承認テスト 1-2-3',
                'phone': '03-1234-5678',
                'fax': '03-1234-5679',
                'email': 'info@approval-test.co.jp',
                'bank_account': '承認テスト銀行 承認テスト支店 普通 1234567'
            }
            
            invoice_data = {
                'project_id': self.test_data['project_id'],
                'client_name': self.test_data['client_name'],
                'project_name': self.test_data['project_name'],
                'billing_amount': self.test_data['billing_amount'],
                'work_description': '承認ワークフローテスト用システム開発業務',
                'notes': 'これは承認ワークフローテスト用の請求書です。',
                'pm_name': self.test_data['requestor']
            }
            
            pdf_path = pdf_generator.generate_single_invoice(
                invoice_data, 
                company_info, 
                "output/invoices"
            )
            
            if not pdf_path or not os.path.exists(pdf_path):
                print("❌ PDF生成失敗")
                return False
            
            self.test_data['pdf_path'] = pdf_path
            self.generated_files.append(pdf_path)
            
            # 承認リクエストの作成
            approval_data = {
                'invoice_id': self.test_data['invoice_id'],
                'project_id': self.test_data['project_id'],
                'client_name': self.test_data['client_name'],
                'project_name': self.test_data['project_name'],
                'billing_amount': self.test_data['billing_amount'],
                'pdf_path': pdf_path,
                'requestor': self.test_data['requestor'],
                'priority': 'normal',
                'due_date': datetime.now() + timedelta(days=2)
            }
            
            approval_request = self.workflow_manager.create_approval_request(approval_data)
            
            if approval_request:
                self.test_data['request_id'] = approval_request.request_id
                self.test_results['workflow_creation'] = True
                print(f"✅ 承認ワークフロー作成成功: {approval_request.request_id}")
                return True
            else:
                print("❌ 承認ワークフロー作成失敗")
                return False
                
        except Exception as e:
            logger.error(f"承認ワークフロー作成エラー: {e}")
            print(f"❌ 承認ワークフロー作成失敗: {e}")
            return False
    
    def test_slack_notification(self):
        """Slack通知テスト"""
        print("\n=== Slack通知テスト ===")
        
        try:
            # 承認依頼データの作成
            approval_request = InvoiceApprovalRequest(
                invoice_id=self.test_data['invoice_id'],
                project_id=self.test_data['project_id'],
                client_name=self.test_data['client_name'],
                project_name=self.test_data['project_name'],
                billing_amount=self.test_data['billing_amount'],
                pdf_path=self.test_data['pdf_path'],
                requestor=self.test_data['requestor'],
                due_date=datetime.now() + timedelta(days=2),
                priority='normal'
            )
            
            # 承認依頼の送信
            success = self.slack_notifier.send_invoice_approval_request(approval_request)
            
            if success:
                self.test_results['slack_notification'] = True
                print("✅ Slack通知送信成功")
                return True
            else:
                print("❌ Slack通知送信失敗")
                return False
                
        except Exception as e:
            logger.error(f"Slack通知エラー: {e}")
            print(f"❌ Slack通知失敗: {e}")
            return False
    
    def test_approval_process(self):
        """承認処理テスト"""
        print("\n=== 承認処理テスト ===")
        
        try:
            request_id = self.test_data['request_id']
            
            # 承認処理のシミュレーション
            success = self.workflow_manager.update_approval_status(
                request_id=request_id,
                status=ApprovalStatus.APPROVED,
                approver=self.test_data['approver']
            )
            
            if success:
                # 承認結果通知の送信
                approval_request = InvoiceApprovalRequest(
                    invoice_id=self.test_data['invoice_id'],
                    project_id=self.test_data['project_id'],
                    client_name=self.test_data['client_name'],
                    project_name=self.test_data['project_name'],
                    billing_amount=self.test_data['billing_amount'],
                    pdf_path=self.test_data['pdf_path'],
                    requestor=self.test_data['requestor'],
                    due_date=datetime.now() + timedelta(days=2),
                    priority='normal'
                )
                
                notification_success = self.slack_notifier.send_approval_result_notification(
                    approval_request, "approved", self.test_data['approver']
                )
                
                if notification_success:
                    self.test_results['approval_process'] = True
                    print("✅ 承認処理成功")
                    return True
                else:
                    print("❌ 承認結果通知送信失敗")
                    return False
            else:
                print("❌ 承認処理失敗")
                return False
                
        except Exception as e:
            logger.error(f"承認処理エラー: {e}")
            print(f"❌ 承認処理失敗: {e}")
            return False
    
    def test_email_sending(self):
        """メール送信テスト"""
        print("\n=== メール送信テスト ===")
        
        try:
            email_sender = GmailEmailSender()
            if not email_sender.authenticate():
                print("❌ Gmail認証失敗")
                return False
            email_data = email_sender.prepare_email_data(
                invoice_id=self.test_data['invoice_id'],
                project_id=self.test_data['project_id'],
                client_name=self.test_data['client_name'],
                project_name=self.test_data['project_name'],
                billing_amount=self.test_data['billing_amount'],
                billing_period=self.test_data['billing_period'],
                due_date=self.test_data['due_date'],
                pdf_path=self.test_data.get('pdf_path', ''),
                custom_message="承認ワークフローテスト送信メールです。"
            )
            success = email_sender.send_invoice_email(email_data)
            
            if success:
                self.test_results['email_sending'] = True
                print("✅ メール送信成功")
                return True
            else:
                print("❌ メール送信失敗")
                return False
                
        except Exception as e:
            logger.error(f"メール送信エラー: {e}")
            print(f"❌ メール送信失敗: {e}")
            return False
    
    def run_full_approval_workflow_test(self):
        """完全な承認ワークフローテストの実行"""
        print("承認ワークフロー統合テスト開始")
        print("=" * 60)
        print("テスト内容: ワークフロー作成 → Slack通知 → 承認処理 → メール送信")
        print("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # 1. テストデータ準備
            if not self.setup_test_data():
                return False
            
            # 2. 承認ワークフロー作成
            if not self.test_workflow_creation():
                return False
            
            # 3. Slack通知
            if not self.test_slack_notification():
                return False
            
            # 4. 承認処理
            if not self.test_approval_process():
                return False
            
            # 5. メール送信
            if not self.test_email_sending():
                return False
            
            # テスト完了
            end_time = datetime.now()
            duration = end_time - start_time
            
            print("\n" + "=" * 60)
            print("🎉 承認ワークフローテスト完了！")
            print("=" * 60)
            
            # 結果表示
            successful_tests = sum(self.test_results.values())
            total_tests = len(self.test_results)
            
            print(f"実行時間: {duration.total_seconds():.2f}秒")
            print(f"成功: {successful_tests}/{total_tests}")
            
            print("\n📊 詳細結果:")
            for test_name, result in self.test_results.items():
                status = "✅ 成功" if result else "❌ 失敗"
                print(f"  {test_name}: {status}")
            
            if successful_tests == total_tests:
                print("\n🎯 すべてのテストが成功しました！")
                print("承認ワークフローは正常に動作しています。")
            else:
                print("\n⚠️ 一部のテストが失敗しました。")
                print("ログを確認して問題を特定してください。")
            
            return successful_tests == total_tests
            
        except Exception as e:
            logger.error(f"承認ワークフローテストエラー: {e}")
            print(f"\n❌ 承認ワークフローテストでエラーが発生しました: {e}")
            return False

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip approval workflow integration tests with external services in CI")
def test_approval_workflow_integration():
    """承認ワークフロー統合テストの実行"""
    approval_test = ApprovalWorkflowTest()
    success = approval_test.run_full_approval_workflow_test()
    assert success, "承認ワークフロー統合テストが失敗しました"

def test_workflow_creation():
    """承認ワークフロー作成テスト"""
    approval_test = ApprovalWorkflowTest()
    approval_test.setup_test_data()
    success = approval_test.test_workflow_creation()
    assert success, "承認ワークフロー作成テストが失敗しました"

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_approval_slack_notification():
    """承認Slack通知テスト"""
    approval_test = ApprovalWorkflowTest()
    approval_test.setup_test_data()
    success = approval_test.test_slack_notification()
    assert success, "承認Slack通知テストが失敗しました"

def test_approval_process():
    """承認処理テスト"""
    approval_test = ApprovalWorkflowTest()
    approval_test.setup_test_data()
    approval_test.test_workflow_creation()
    success = approval_test.test_approval_process()
    assert success, "承認処理テストが失敗しました"

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_approval_email_sending():
    """承認メール送信テスト"""
    approval_test = ApprovalWorkflowTest()
    approval_test.setup_test_data()
    success = approval_test.test_email_sending()
    assert success, "承認メール送信テストが失敗しました"

def main():
    """メイン処理"""
    approval_test = ApprovalWorkflowTest()
    success = approval_test.run_full_approval_workflow_test()
    
    if success:
        print("\n🚀 承認ワークフローテストが成功しました！")
        print("承認ワークフローは本格運用の準備ができています。")
    else:
        print("\n🔧 承認ワークフローテストに失敗しました。")
        print("問題を修正してから再実行してください。")

if __name__ == "__main__":
    main() 