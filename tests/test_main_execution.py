import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
test_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, test_root)

import src.main_execution as main_exec
from src.notifications.slack_notifier import SlackMessage

class TestMainExecution(unittest.TestCase):
    @patch('src.main_execution.make_invoice_seed_main')
    @patch('src.main_execution.build_invoice_pdf_main')
    @patch('src.main_execution.invoice_email_sender_main')
    @patch('src.main_execution.SlackNotifier')
    @patch('src.main_execution.InvoiceDraftGenerator')
    @patch('builtins.open', create=True)
    @patch('csv.DictReader')
    def test_run_invoice_generation_success(self, mock_csv_reader, mock_open, mock_ai_generator, mock_slack, mock_email, mock_pdf, mock_seed):
        """請求書生成: 正常系"""
        # モックの設定
        mock_slack.return_value.send_message = MagicMock()
        mock_ai_generator.return_value.generate_draft.return_value = {
            "work_description": "テスト業務",
            "notes": "テスト備考"
        }
        mock_csv_reader.return_value = [
            {"project_name": "テストプロジェクト", "client_name": "テスト株式会社", "billing_amount": "500000", "pm_name": "田中太郎"}
        ]
        
        main_exec.run_invoice_generation()
        
        # 検証
        mock_seed.assert_called_once()
        mock_pdf.assert_called_once()
        mock_email.assert_called_once()
        mock_ai_generator.return_value.generate_draft.assert_called_once()
        mock_slack.return_value.send_message.assert_called_once()
        
        # SlackMessageオブジェクトが渡されることを確認
        call_args = mock_slack.return_value.send_message.call_args[0][0]
        self.assertIsInstance(call_args, SlackMessage)
        self.assertIn("請求書生成処理が正常に完了しました", call_args.text)

    @patch('src.main_execution.make_invoice_seed_main', side_effect=Exception("seed error"))
    @patch('src.main_execution.SlackNotifier')
    def test_run_invoice_generation_error(self, mock_slack, mock_seed):
        """請求書生成: エラー系"""
        mock_slack.return_value.send_message = MagicMock()
        # 例外が発生することを確認
        with self.assertRaises(Exception):
            main_exec.run_invoice_generation()
        mock_slack.return_value.send_message.assert_called()

    @patch('src.main_execution.prep_bank_txn_main')
    @patch('src.main_execution.SlackNotifier')
    @patch('src.main_execution.PaymentMatcher')
    @patch('builtins.open', create=True)
    @patch('csv.DictReader')
    @patch('json.load')
    def test_run_payment_matching_success(self, mock_json_load, mock_csv_reader, mock_open, mock_ai_matcher, mock_slack, mock_prep):
        """入金マッチング: 正常系"""
        # モックの設定
        mock_slack.return_value.send_message = MagicMock()
        mock_ai_matcher.return_value.match.return_value = [
            {
                "invoice_id": "INV_001",
                "payment_id": "PAY_001",
                "match_type": "exact",
                "confidence_score": 1.0,
                "match_amount": 300000,
                "status": "confirmed"
            }
        ]
        mock_json_load.return_value = [
            {"invoice_id": "INV_001", "client_name": "テスト株式会社", "billing_amount": 300000}
        ]
        mock_csv_reader.return_value = [
            {"payment_id": "PAY_001", "client_name": "テスト株式会社", "payment_amount": "300000"}
        ]
        
        main_exec.run_payment_matching()
        
        # 検証
        mock_prep.assert_called_once()
        mock_ai_matcher.return_value.match.assert_called_once()
        mock_slack.return_value.send_message.assert_called_once()
        
        # SlackMessageオブジェクトが渡されることを確認
        call_args = mock_slack.return_value.send_message.call_args[0][0]
        self.assertIsInstance(call_args, SlackMessage)
        self.assertIn("入金マッチング処理が正常に完了しました", call_args.text)

    @patch('src.main_execution.prep_bank_txn_main', side_effect=Exception("prep error"))
    @patch('src.main_execution.SlackNotifier')
    def test_run_payment_matching_error(self, mock_slack, mock_prep):
        """入金マッチング: エラー系"""
        mock_slack.return_value.send_message = MagicMock()
        # 例外が発生することを確認
        with self.assertRaises(Exception):
            main_exec.run_payment_matching()
        mock_slack.return_value.send_message.assert_called()

if __name__ == '__main__':
    unittest.main() 