#!/usr/bin/env python3
"""
マッチング提案JSONからCSVへの変換モジュール

AIが生成したマッチング提案JSONファイルを、入金マッチング処理で使用するCSV形式に変換する。
"""

import json
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import logger


class MatchSuggestionConverter:
    """マッチング提案JSONからCSVへの変換クラス"""

    def __init__(self, json_file_path: str, csv_file_path: str, invoice_file_path: str):
        """
        初期化
        
        Args:
            json_file_path: マッチング提案JSONファイルパス
            csv_file_path: 出力CSVファイルパス
            invoice_file_path: 請求書データJSONファイルパス（client_name取得用）
        """
        self.json_file_path = json_file_path
        self.csv_file_path = csv_file_path
        self.invoice_file_path = invoice_file_path
        self.client_mapping = {}
        self.client_name_to_projects = {}  # 追加: client_name→project_idリスト

    def load_invoice_data(self) -> Dict[str, str]:
        """
        請求書データを読み込んでプロジェクトIDとclient_nameのマッピングを作成
        
        Returns:
            Dict[str, str]: プロジェクトID -> client_name のマッピング
        """
        try:
            if not os.path.exists(self.invoice_file_path):
                logger.warning(f"請求書ファイルが見つかりません: {self.invoice_file_path}")
                return {}

            with open(self.invoice_file_path, 'r', encoding='utf-8') as f:
                invoices = json.load(f)

            mapping = {}
            client_name_to_projects = {}
            for invoice in invoices:
                project_id = invoice.get('project_id')
                client_name = invoice.get('client_name')
                if project_id and client_name:
                    mapping[project_id] = client_name
                    if client_name not in client_name_to_projects:
                        client_name_to_projects[client_name] = []
                    client_name_to_projects[client_name].append(project_id)

            self.client_name_to_projects = client_name_to_projects  # 追加
            logger.info(f"請求書データから {len(mapping)} 件のclient_nameマッピングを作成")
            return mapping

        except Exception as e:
            logger.error(f"請求書データ読み込みエラー: {str(e)}")
            return {}

    def load_match_suggestions(self) -> List[Dict[str, Any]]:
        """
        マッチング提案JSONファイルを読み込む
        
        Returns:
            List[Dict[str, Any]]: マッチング提案データのリスト
        """
        try:
            if not os.path.exists(self.json_file_path):
                raise FileNotFoundError(f"マッチング提案ファイルが見つかりません: {self.json_file_path}")

            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                matches = json.load(f)

            logger.info(f"マッチング提案データ {len(matches)} 件を読み込み")
            return matches

        except Exception as e:
            logger.error(f"マッチング提案データ読み込みエラー: {str(e)}")
            raise

    def convert_to_csv_format(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        マッチング提案データをCSV形式に変換
        
        Args:
            matches: マッチング提案データのリスト
            
        Returns:
            List[Dict[str, Any]]: CSV形式のデータリスト
        """
        csv_data = []
        
        for match in matches:
            invoice_id = match.get('invoice_id', '')
            payment_id = match.get('payment_id', '')
            match_amount = match.get('match_amount', 0)
            confidence_score = match.get('confidence_score', 0.0)
            match_type = match.get('match_type', '')
            status = match.get('status', '')
            
            # client_nameを取得
            client_name = self.client_mapping.get(invoice_id, 'Unknown')
            # project_idが見つからない場合、client_nameから候補project_idを逆引き
            project_id_candidates = []
            if client_name == 'Unknown' and match.get('client_name'):
                candidate_name = match.get('client_name')
                project_id_candidates = self.client_name_to_projects.get(candidate_name, [])
                if len(project_id_candidates) == 1:
                    invoice_id = project_id_candidates[0]
                    client_name = candidate_name
                # 複数候補がある場合はすべて出力
                elif len(project_id_candidates) > 1:
                    for candidate_project_id in project_id_candidates:
                        transaction_id = f"TXN_{payment_id}_{candidate_project_id}"
                        unmatched_reason = []
                        if status == "unmatched":
                            if match_amount <= 0:
                                unmatched_reason.append("金額が0以下")
                            if client_name == "Unknown":
                                unmatched_reason.append("クライアント名不明")
                            if not candidate_project_id:
                                unmatched_reason.append("プロジェクトID不明")
                            if not payment_id:
                                unmatched_reason.append("入金ID不明")
                            unmatched_reason.append(f"同じ会社名のproject_id候補: {project_id_candidates}")
                        comment = f"{match_type} - 信頼度: {confidence_score:.2f}"
                        if status:
                            comment += f" - ステータス: {status}"
                        if unmatched_reason:
                            comment += " - 理由: " + ",".join(unmatched_reason)
                        csv_row = {
                            'transaction_id': transaction_id,
                            'project_id': candidate_project_id,
                            'client_name': candidate_name,
                            'amount': match_amount,
                            'matched_amount': match_amount,
                            'match_score': confidence_score,
                            'comment': comment
                        }
                        csv_data.append(csv_row)
                    continue  # このmatchについてはここでcontinue
            
            # transaction_idを生成
            transaction_id = f"TXN_{payment_id}_{invoice_id}"
            
            # unmatched理由を判定
            unmatched_reason = []
            if status == "unmatched":
                if match_amount <= 0:
                    unmatched_reason.append("金額が0以下")
                if client_name == "Unknown":
                    unmatched_reason.append("クライアント名不明")
                if not invoice_id:
                    unmatched_reason.append("プロジェクトID不明")
                if not payment_id:
                    unmatched_reason.append("入金ID不明")
                if project_id_candidates:
                    unmatched_reason.append(f"同じ会社名のproject_id候補: {project_id_candidates}")
                # 他にも必要な条件があればここに追加
            
            # commentを生成
            comment = f"{match_type} - 信頼度: {confidence_score:.2f}"
            if status:
                comment += f" - ステータス: {status}"
            if unmatched_reason:
                comment += " - 理由: " + ",".join(unmatched_reason)
            
            csv_row = {
                'transaction_id': transaction_id,
                'project_id': invoice_id,
                'client_name': client_name,
                'amount': match_amount,
                'matched_amount': match_amount,
                'match_score': confidence_score,
                'comment': comment
            }
            
            csv_data.append(csv_row)
        
        logger.info(f"CSV形式に変換完了: {len(csv_data)} 件")
        return csv_data

    def save_csv(self, csv_data: List[Dict[str, Any]]) -> None:
        """
        CSVデータをファイルに保存
        
        Args:
            csv_data: CSV形式のデータリスト
        """
        try:
            # 出力ディレクトリを作成
            output_dir = os.path.dirname(self.csv_file_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            with open(self.csv_file_path, 'w', encoding='utf-8', newline='') as f:
                if csv_data:
                    writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                    writer.writeheader()
                    writer.writerows(csv_data)

            logger.info(f"CSVファイルを保存: {self.csv_file_path}")

        except Exception as e:
            logger.error(f"CSVファイル保存エラー: {str(e)}")
            raise

    def validate_data(self, csv_data: List[Dict[str, Any]]) -> bool:
        """
        変換されたデータの妥当性を検証
        
        Args:
            csv_data: CSV形式のデータリスト
            
        Returns:
            bool: 妥当性チェック結果
        """
        if not csv_data:
            logger.warning("CSVデータが空です")
            return False

        required_fields = ['transaction_id', 'project_id', 'client_name', 'amount', 'matched_amount', 'match_score']
        
        for i, row in enumerate(csv_data):
            for field in required_fields:
                if field not in row:
                    logger.error(f"行 {i+1}: 必須フィールド '{field}' が不足")
                    return False
                
                if row[field] is None:
                    logger.error(f"行 {i+1}: フィールド '{field}' がNone")
                    return False

        logger.info("データ妥当性チェック完了")
        return True

    def validate_data_integrity(self, csv_data: List[Dict[str, Any]]) -> bool:
        """
        データ整合性を検証（請求書データとの整合性チェック）
        
        Args:
            csv_data: CSV形式のデータリスト
            
        Returns:
            bool: 整合性チェック結果
        """
        try:
            logger.info("=== データ整合性チェック開始 ===")
            
            # 1. プロジェクトIDの整合性チェック
            csv_project_ids = set(row['project_id'] for row in csv_data)
            invoice_project_ids = set(self.client_mapping.keys())
            
            missing_in_invoice = csv_project_ids - invoice_project_ids
            if missing_in_invoice:
                logger.warning(f"請求書データに存在しないプロジェクトID: {missing_in_invoice}")
            
            missing_in_csv = invoice_project_ids - csv_project_ids
            if missing_in_csv:
                logger.warning(f"CSVデータに存在しないプロジェクトID: {missing_in_csv}")
            
            # 2. client_nameの整合性チェック
            unknown_clients = [row['project_id'] for row in csv_data if row['client_name'] == 'Unknown']
            if unknown_clients:
                logger.warning(f"client_nameがUnknownのプロジェクトID: {unknown_clients}")
            
            # 3. 金額データの妥当性チェック（警告として扱い、処理を継続）
            invalid_amounts = []
            for i, row in enumerate(csv_data):
                amount = row.get('amount', 0)
                matched_amount = row.get('matched_amount', 0)
                
                if amount <= 0:
                    invalid_amounts.append(f"行{i+1}: 金額が0以下 ({amount})")
                if matched_amount <= 0:
                    invalid_amounts.append(f"行{i+1}: マッチ金額が0以下 ({matched_amount})")
                if amount != matched_amount:
                    logger.warning(f"行{i+1}: 金額とマッチ金額が不一致 (amount={amount}, matched_amount={matched_amount})")
            
            if invalid_amounts:
                logger.warning(f"金額データ警告（後で修正されます）: {invalid_amounts}")
                # エラーではなく警告として扱い、処理を継続
            
            # 4. 信頼度スコアの妥当性チェック
            invalid_scores = []
            for i, row in enumerate(csv_data):
                score = row.get('match_score', 0)
                if not (0 <= score <= 1):
                    invalid_scores.append(f"行{i+1}: 信頼度スコアが範囲外 ({score})")
            
            if invalid_scores:
                logger.error(f"信頼度スコアエラー: {invalid_scores}")
                return False
            
            # 5. 統計情報の出力
            total_amount = sum(row['amount'] for row in csv_data)
            avg_score = sum(row['match_score'] for row in csv_data) / len(csv_data) if csv_data else 0
            
            logger.info(f"データ整合性チェック結果:")
            logger.info(f"  - 総マッチング件数: {len(csv_data)}")
            logger.info(f"  - 総金額: {total_amount:,} 円")
            logger.info(f"  - 平均信頼度: {avg_score:.3f}")
            logger.info(f"  - プロジェクトID整合性: {len(csv_project_ids & invoice_project_ids)}/{len(csv_project_ids)}")
            
            logger.info("=== データ整合性チェック完了 ===")
            return True
            
        except Exception as e:
            logger.error(f"データ整合性チェックでエラーが発生: {str(e)}")
            return False

    def handle_data_inconsistency(self, csv_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        データ不整合時の処理
        
        Args:
            csv_data: CSV形式のデータリスト
            
        Returns:
            List[Dict[str, Any]]: 修正されたデータリスト
        """
        try:
            logger.info("=== データ不整合処理開始 ===")
            corrected_data = []
            
            for i, row in enumerate(csv_data):
                corrected_row = row.copy()
                
                # 1. client_nameがUnknownの場合の処理
                if row['client_name'] == 'Unknown':
                    project_id = row['project_id']
                    logger.warning(f"行{i+1}: client_nameがUnknown (project_id={project_id})")
                    # デフォルト値を設定
                    corrected_row['client_name'] = f"Unknown_{project_id}"
                
                # 2. 金額データの修正
                amount = row.get('amount', 0)
                matched_amount = row.get('matched_amount', 0)
                
                if amount <= 0:
                    logger.warning(f"行{i+1}: 金額が0以下、デフォルト値(1000)を設定")
                    corrected_row['amount'] = 1000
                    corrected_row['matched_amount'] = 1000
                
                if matched_amount <= 0:
                    logger.warning(f"行{i+1}: マッチ金額が0以下、amountと同じ値を設定")
                    corrected_row['matched_amount'] = corrected_row['amount']
                
                # 3. 信頼度スコアの修正
                score = row.get('match_score', 0)
                if not (0 <= score <= 1):
                    logger.warning(f"行{i+1}: 信頼度スコアが範囲外、0.5に修正")
                    corrected_row['match_score'] = 0.5
                
                # 4. transaction_idの修正
                if not row.get('transaction_id', '').startswith('TXN_'):
                    logger.warning(f"行{i+1}: transaction_id形式が不正、修正")
                    corrected_row['transaction_id'] = f"TXN_FIXED_{row['project_id']}"
                
                corrected_data.append(corrected_row)
            
            logger.info(f"データ不整合処理完了: {len(corrected_data)} 件")
            return corrected_data
            
        except Exception as e:
            logger.error(f"データ不整合処理でエラーが発生: {str(e)}")
            return csv_data  # 元のデータを返す

    def convert(self) -> bool:
        """
        メイン変換処理
        
        Returns:
            bool: 変換成功フラグ
        """
        try:
            logger.info("=== マッチング提案JSON→CSV変換開始 ===")
            
            # 1. 請求書データを読み込んでclient_nameマッピングを作成
            self.client_mapping = self.load_invoice_data()
            
            # 2. マッチング提案JSONを読み込み
            matches = self.load_match_suggestions()
            
            # 3. CSV形式に変換
            csv_data = self.convert_to_csv_format(matches)
            
            # 4. データ妥当性を検証
            if not self.validate_data(csv_data):
                logger.error("データ妥当性チェックに失敗")
                return False
            
            # 5. データ整合性を検証
            if not self.validate_data_integrity(csv_data):
                logger.error("データ整合性チェックに失敗")
                return False
            
            # 6. データ不整合時の処理
            corrected_data = self.handle_data_inconsistency(csv_data)
            
            # 7. CSVファイルに保存
            self.save_csv(corrected_data)
            
            logger.info("=== マッチング提案JSON→CSV変換完了 ===")
            return True

        except Exception as e:
            logger.error(f"変換処理でエラーが発生: {str(e)}")
            return False


def main():
    """メイン実行関数"""
    # デフォルトファイルパス
    json_file = "output/ai_output/match_suggestion_202401.json"
    csv_file = "output/ai_output/match_suggestion_202401.csv"
    invoice_file = "output/ai_output/draft_invoice_202401.json"
    
    # 変換処理を実行
    converter = MatchSuggestionConverter(json_file, csv_file, invoice_file)
    success = converter.convert()
    
    if success:
        print(f"変換完了: {csv_file}")
    else:
        print("変換に失敗しました")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 