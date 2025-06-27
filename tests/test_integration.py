#!/usr/bin/env python3
"""
統合テストスクリプト
請求書生成 → PDF出力 → Slack承認 → メール送信の一連の流れをテスト
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytest

# 各モジュールのインポート
from src.pdf_generation.build_invoice_pdf import InvoicePDFGenerator
from src.notifications.slack_notifier import SlackNotifier, InvoiceApprovalRequest
from src.email_utils.invoice_email_sender import GmailEmailSender
from utils.logger import logger

class IntegrationTest:
    """統合テストクラス"""
    
    def __init__(self):
        self.test_results = {
            'invoice_generation': False,
            'pdf_creation': False,
            'slack_notification': False,
            'email_sending': False
        }
        self.generated_files = []
        self.test_data = {}
    
    def setup_test_data(self):
        """テストデータの準備"""
        print("=== テストデータ準備 ===")
        
        # テスト用の請求書データ
        self.test_data = {
            'invoice_id': f"INV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'project_id': 'PRJ_INTEGRATION_TEST',
            'client_name': '統合テスト株式会社',
            'project_name': '統合テストプロジェクト',
            'billing_amount': 250000,
            'billing_period': '2025年6月',
            'due_date': (datetime.now() + timedelta(days=30)).strftime('%Y年%m月%d日'),
            'requestor': '高山 完治',
            'recipient_email': 'kanji.takayama@gmail.com',
            'recipient_name': '高山 完治',
            'recipient_company': '統合テスト株式会社'
        }
        
        print(f"✅ テストデータ準備完了")
        print(f"   請求書ID: {self.test_data['invoice_id']}")
        print(f"   プロジェクト: {self.test_data['project_name']}")
        print(f"   請求金額: ¥{self.test_data['billing_amount']:,}")
        
        return True
    
    def test_invoice_generation(self):
        """請求書データ生成テスト"""
        print("\n=== 請求書データ生成テスト ===")
        
        try:
            # テスト用の請求書データを生成
            invoice_data = {
                'invoice_id': self.test_data['invoice_id'],
                'project_id': self.test_data['project_id'],
                'client_name': self.test_data['client_name'],
                'project_name': self.test_data['project_name'],
                'billing_amount': self.test_data['billing_amount'],
                'billing_period': self.test_data['billing_period'],
                'due_date': self.test_data['due_date'],
                'status': 'pending_approval'
            }
            
            # 請求書データを保存
            output_path = f"output/ai_output/invoice_data_{self.test_data['invoice_id']}.json"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(invoice_data, f, ensure_ascii=False, indent=2)
            
            self.generated_files.append(output_path)
            self.test_results['invoice_generation'] = True
            
            print(f"✅ 請求書データ生成成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"請求書データ生成エラー: {e}")
            print(f"❌ 請求書データ生成失敗: {e}")
            return False
    
    def test_pdf_creation(self):
        """PDF生成テスト"""
        print("\n=== PDF生成テスト ===")
        
        try:
            # PDFジェネレーターの初期化
            pdf_generator = InvoicePDFGenerator()
            
            # 会社情報の設定
            company_info = {
                'name': '統合テスト株式会社',
                'address': '東京都渋谷区テスト 1-2-3',
                'phone': '03-1234-5678',
                'fax': '03-1234-5679',
                'email': 'info@integration-test.co.jp',
                'bank_account': 'テスト銀行 テスト支店 普通 1234567'
            }
            
            # 請求書データの準備
            invoice_data = {
                'project_id': self.test_data['project_id'],
                'client_name': self.test_data['client_name'],
                'project_name': self.test_data['project_name'],
                'billing_amount': self.test_data['billing_amount'],
                'work_description': '統合テスト用システム開発業務',
                'notes': 'これは統合テスト用の請求書です。',
                'pm_name': '高山 完治'
            }
            
            # PDF生成
            output_path = pdf_generator.generate_single_invoice(
                invoice_data, 
                company_info, 
                "output/invoices"
            )
            
            if output_path and os.path.exists(output_path):
                self.generated_files.append(output_path)
                self.test_data['pdf_path'] = output_path
                self.test_results['pdf_creation'] = True
                
                print(f"✅ PDF生成成功: {output_path}")
                return True
            else:
                print("❌ PDF生成失敗: ファイルが作成されませんでした")
                return False
                
        except Exception as e:
            logger.error(f"PDF生成エラー: {e}")
            print(f"❌ PDF生成失敗: {e}")
            return False
    
    def test_slack_notification(self):
        """Slack通知テスト"""
        print("\n=== Slack通知テスト ===")
        
        try:
            # Slack通知クラスの初期化
            slack_notifier = SlackNotifier()
            
            # 承認依頼データの作成
            approval_request = InvoiceApprovalRequest(
                invoice_id=self.test_data['invoice_id'],
                project_id=self.test_data['project_id'],
                client_name=self.test_data['client_name'],
                project_name=self.test_data['project_name'],
                billing_amount=self.test_data['billing_amount'],
                pdf_path=self.test_data.get('pdf_path', ''),
                requestor=self.test_data['requestor'],
                due_date=datetime.now() + timedelta(days=2),
                priority='normal'
            )
            
            # 承認依頼の送信
            success = slack_notifier.send_invoice_approval_request(approval_request)
            
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
                custom_message="統合テスト送信メールです。"
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
    
    def cleanup_test_files(self):
        """テストファイルのクリーンアップ"""
        print("\n=== テストファイルクリーンアップ ===")
        
        cleaned_count = 0
        for file_path in self.generated_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
                    print(f"🗑️ 削除: {file_path}")
            except Exception as e:
                print(f"⚠️ 削除失敗: {file_path} - {e}")
        
        print(f"✅ {cleaned_count}個のファイルをクリーンアップしました")
    
    def run_full_integration_test(self):
        """完全な統合テストの実行"""
        print("統合テスト開始")
        print("=" * 60)
        print("テスト内容: 請求書生成 → PDF出力 → Slack承認 → メール送信")
        print("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # 1. テストデータ準備
            if not self.setup_test_data():
                return False
            
            # 2. 請求書データ生成
            if not self.test_invoice_generation():
                return False
            
            # 3. PDF生成
            if not self.test_pdf_creation():
                return False
            
            # 4. Slack通知
            if not self.test_slack_notification():
                return False
            
            # 5. メール送信
            if not self.test_email_sending():
                return False
            
            # テスト完了
            end_time = datetime.now()
            duration = end_time - start_time
            
            print("\n" + "=" * 60)
            print("🎉 統合テスト完了！")
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
                print("システムは正常に動作しています。")
            else:
                print("\n⚠️ 一部のテストが失敗しました。")
                print("ログを確認して問題を特定してください。")
            
            return successful_tests == total_tests
            
        except Exception as e:
            logger.error(f"統合テストエラー: {e}")
            print(f"\n❌ 統合テストでエラーが発生しました: {e}")
            return False
        
        finally:
            # クリーンアップ（オプション）
            # self.cleanup_test_files()
            pass

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip integration tests with external services in CI")
def test_integration_workflow():
    """統合テストの実行"""
    integration_test = IntegrationTest()
    success = integration_test.run_full_integration_test()
    assert success, "統合テストが失敗しました"

def test_invoice_generation():
    """請求書生成テスト"""
    integration_test = IntegrationTest()
    integration_test.setup_test_data()
    success = integration_test.test_invoice_generation()
    assert success, "請求書生成テストが失敗しました"

def test_pdf_creation():
    """PDF生成テスト"""
    integration_test = IntegrationTest()
    integration_test.setup_test_data()
    integration_test.test_invoice_generation()
    success = integration_test.test_pdf_creation()
    assert success, "PDF生成テストが失敗しました"

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_slack_notification():
    """Slack通知テスト"""
    integration_test = IntegrationTest()
    integration_test.setup_test_data()
    success = integration_test.test_slack_notification()
    assert success, "Slack通知テストが失敗しました"

@pytest.mark.skipif(os.getenv('CI') == 'true', reason="Skip external service tests in CI")
def test_email_sending():
    """メール送信テスト"""
    integration_test = IntegrationTest()
    integration_test.setup_test_data()
    success = integration_test.test_email_sending()
    assert success, "メール送信テストが失敗しました"

def main():
    """メイン処理"""
    integration_test = IntegrationTest()
    success = integration_test.run_full_integration_test()
    
    if success:
        print("\n🚀 統合テストが成功しました！システムは本格運用の準備ができています。")
    else:
        print("\n🔧 統合テストに失敗しました。問題を修正してから再実行してください。")

if __name__ == "__main__":
    main() 