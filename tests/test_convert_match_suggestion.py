#!/usr/bin/env python3
"""
マッチング提案JSON→CSV変換処理のテスト
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_processing.convert_match_suggestion import MatchSuggestionConverter


def create_test_invoice_data():
    """テスト用の請求書データを作成"""
    return [
        {
            "project_id": "PRJ_0001",
            "client_name": "株式会社テストA",
            "billing_amount": 100000
        },
        {
            "project_id": "PRJ_0002", 
            "client_name": "株式会社テストB",
            "billing_amount": 200000
        }
    ]


def create_test_match_data():
    """テスト用のマッチング提案データを作成"""
    return [
        {
            "invoice_id": "PRJ_0001",
            "payment_id": "2024-01-15",
            "match_type": "完全一致",
            "confidence_score": 1.0,
            "match_amount": 100000,
            "status": "マッチ"
        },
        {
            "invoice_id": "PRJ_0002",
            "payment_id": "2024-01-16", 
            "match_type": "部分一致",
            "confidence_score": 0.8,
            "match_amount": 200000,
            "status": "マッチ"
        }
    ]


class TestMatchSuggestionConverter:
    """MatchSuggestionConverterクラスのテスト"""

    def setup_method(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.json_file = os.path.join(self.temp_dir, "test_match.json")
        self.csv_file = os.path.join(self.temp_dir, "test_match.csv")
        self.invoice_file = os.path.join(self.temp_dir, "test_invoice.json")
        
        # テストデータを作成
        with open(self.invoice_file, 'w', encoding='utf-8') as f:
            json.dump(create_test_invoice_data(), f, ensure_ascii=False, indent=2)
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(create_test_match_data(), f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_invoice_data(self):
        """請求書データ読み込みのテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        mapping = converter.load_invoice_data()
        
        assert len(mapping) == 2
        assert mapping["PRJ_0001"] == "株式会社テストA"
        assert mapping["PRJ_0002"] == "株式会社テストB"

    def test_load_match_suggestions(self):
        """マッチング提案データ読み込みのテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        matches = converter.load_match_suggestions()
        
        assert len(matches) == 2
        assert matches[0]["invoice_id"] == "PRJ_0001"
        assert matches[1]["invoice_id"] == "PRJ_0002"

    def test_convert_to_csv_format(self):
        """CSV形式変換のテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        converter.client_mapping = converter.load_invoice_data()
        matches = converter.load_match_suggestions()
        
        csv_data = converter.convert_to_csv_format(matches)
        
        assert len(csv_data) == 2
        assert csv_data[0]["project_id"] == "PRJ_0001"
        assert csv_data[0]["client_name"] == "株式会社テストA"
        assert csv_data[0]["amount"] == 100000
        assert csv_data[0]["match_score"] == 1.0
        assert csv_data[0]["transaction_id"] == "TXN_2024-01-15_PRJ_0001"

    def test_validate_data(self):
        """データ妥当性チェックのテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        converter.client_mapping = converter.load_invoice_data()
        matches = converter.load_match_suggestions()
        csv_data = converter.convert_to_csv_format(matches)
        
        # 正常なデータのテスト
        assert converter.validate_data(csv_data) is True
        
        # 不正なデータのテスト
        invalid_data = csv_data.copy()
        invalid_data[0]["amount"] = None
        assert converter.validate_data(invalid_data) is False

    def test_validate_data_integrity(self):
        """データ整合性チェックのテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        converter.client_mapping = converter.load_invoice_data()
        matches = converter.load_match_suggestions()
        csv_data = converter.convert_to_csv_format(matches)
        
        # 正常なデータのテスト
        assert converter.validate_data_integrity(csv_data) is True
        
        # 不整合データのテスト
        inconsistent_data = csv_data.copy()
        inconsistent_data[0]["client_name"] = "Unknown"
        assert converter.validate_data_integrity(inconsistent_data) is True  # 警告は出るが失敗しない

    def test_handle_data_inconsistency(self):
        """データ不整合処理のテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        
        # 不整合データを作成
        inconsistent_data = [
            {
                "transaction_id": "TXN_2024-01-15_PRJ_0001",
                "project_id": "PRJ_0001",
                "client_name": "Unknown",
                "amount": 0,
                "matched_amount": -100,
                "match_score": 1.5,
                "comment": "テスト"
            }
        ]
        
        corrected_data = converter.handle_data_inconsistency(inconsistent_data)
        
        assert corrected_data[0]["client_name"] == "Unknown_PRJ_0001"
        assert corrected_data[0]["amount"] == 1000
        assert corrected_data[0]["matched_amount"] == 1000
        assert corrected_data[0]["match_score"] == 0.5

    def test_save_csv(self):
        """CSV保存のテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        converter.client_mapping = converter.load_invoice_data()
        matches = converter.load_match_suggestions()
        csv_data = converter.convert_to_csv_format(matches)
        
        converter.save_csv(csv_data)
        
        assert os.path.exists(self.csv_file)
        
        # CSVファイルの内容を確認
        import csv
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]["project_id"] == "PRJ_0001"
        assert rows[0]["client_name"] == "株式会社テストA"

    def test_convert_full_process(self):
        """完全な変換処理のテスト"""
        converter = MatchSuggestionConverter(self.json_file, self.csv_file, self.invoice_file)
        
        # 変換処理を実行
        success = converter.convert()
        
        assert success is True
        assert os.path.exists(self.csv_file)
        
        # 結果を確認
        import csv
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 2
        assert rows[0]["project_id"] == "PRJ_0001"
        assert rows[0]["client_name"] == "株式会社テストA"
        assert rows[1]["project_id"] == "PRJ_0002"
        assert rows[1]["client_name"] == "株式会社テストB"

    def test_convert_with_missing_files(self):
        """ファイルが存在しない場合のテスト"""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.json")
        converter = MatchSuggestionConverter(non_existent_file, self.csv_file, self.invoice_file)
        
        # 変換処理を実行
        success = converter.convert()
        
        assert success is False

    def test_convert_with_invalid_json(self):
        """不正なJSONファイルのテスト"""
        invalid_json_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_json_file, 'w', encoding='utf-8') as f:
            f.write("invalid json content")
        
        converter = MatchSuggestionConverter(invalid_json_file, self.csv_file, self.invoice_file)
        
        # 変換処理を実行
        success = converter.convert()
        
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__]) 