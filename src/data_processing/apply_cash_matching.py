"""
apply_cash_matching.py

AIマッチング提案・銀行データ・請求書シードデータを突合・検証し、
仕訳データを生成するための前処理・バリデーション・集計を行うモジュール。
"""
import pandas as pd
import os
from datetime import datetime
from typing import Dict, Tuple
from utils.logger import logger
from config.constants import CONFIDENCE_THRESHOLD_DEFAULT, MATCH_SCORE_MIN, MATCH_SCORE_MAX


def log_processing_stage(stage_name: str, data_info: Dict):
    """処理段階のログを出力"""
    logger.debug(f"=== {stage_name} ===")
    for key, value in data_info.items():
        if isinstance(value, (int, float)) and key.endswith('amount'):
            logger.debug(f"{key}: {value:,} 円")
        elif isinstance(value, float):
            logger.debug(f"{key}: {value:.3f}")
        else:
            logger.debug(f"{key}: {value}")
    logger.debug(f"=== {stage_name} 完了 ===\n")


class CashMatchingProcessor:
    """
    AIマッチング提案・銀行データ・請求書シードデータを突合・検証し、
    仕訳データを生成するための前処理・バリデーション・集計を行うクラス。

    Attributes:
        match_suggestion_file (str): マッチング提案CSVファイルパス
        bank_data_file (str): 銀行データCSVファイルパス
        invoice_seed_file (str): 請求書シードCSVファイルパス
        match_df (pd.DataFrame): マッチング提案データ
        bank_df (pd.DataFrame): 銀行データ
        invoice_df (pd.DataFrame): 請求書シードデータ
        processing_stats (dict): 処理統計
    """

    def __init__(
            self,
            match_suggestion_file: str,
            bank_data_file: str,
            invoice_seed_file: str):
        self.match_suggestion_file = match_suggestion_file
        self.bank_data_file = bank_data_file
        self.invoice_seed_file = invoice_seed_file
        self.match_df = None
        self.bank_df = None
        self.invoice_df = None
        self.journal_df = None
        self.processing_stats = {
            'total_suggestions': 0,
            'applied_matches': 0,
            'rejected_matches': 0,
            'total_amount': 0,
            'matched_amount': 0
        }

    def load_data(self) -> bool:
        """データの読み込み"""
        try:
            # マッチング提案データの読み込み
            if os.path.exists(self.match_suggestion_file):
                self.match_df = pd.read_csv(
                    self.match_suggestion_file, encoding='utf-8')
                logger.debug(
                    f"Loaded match suggestions: {len(self.match_df)} rows")
            else:
                logger.error(
                    f"Match suggestion file not found: {self.match_suggestion_file}")
                return False

            # 銀行データの読み込み
            if os.path.exists(self.bank_data_file):
                self.bank_df = pd.read_csv(
                    self.bank_data_file, encoding='utf-8')
                logger.debug(f"Loaded bank data: {len(self.bank_df)} rows")
            else:
                logger.error(
                    f"Bank data file not found: {self.bank_data_file}")
                return False

            # 請求書シードデータの読み込み
            if os.path.exists(self.invoice_seed_file):
                self.invoice_df = pd.read_csv(
                    self.invoice_seed_file, encoding='utf-8')
                logger.debug(
                    f"Loaded invoice seed: {len(self.invoice_df)} rows")
            else:
                logger.error(
                    f"Invoice seed file not found: {self.invoice_seed_file}")
                return False

            # データ読み込み後の差分比較ログ
            data_info = {
                'マッチング提案件数': len(self.match_df),
                '銀行データ件数': len(self.bank_df),
                '請求書シード件数': len(self.invoice_df)
            }

            if self.match_df is not None and 'amount' in self.match_df.columns:
                data_info['マッチング提案総額'] = self.match_df['amount'].sum()

            if self.invoice_df is not None and 'billing_amount' in self.invoice_df.columns:
                data_info['請求書シード総額'] = self.invoice_df['billing_amount'].sum()

            log_processing_stage("データ読み込み完了", data_info)

            return True

        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            return False

    def validate_match_suggestions(self) -> bool:
        """マッチング提案データの検証"""
        required_columns = [
            'transaction_id',
            'project_id',
            'client_name',
            'amount',
            'matched_amount',
            'match_score']

        missing_columns = [
            col for col in required_columns if col not in self.match_df.columns]

        if missing_columns:
            logger.error(
                f"Missing required columns in match suggestions: {missing_columns}")
            return False

        # マッチングスコアの範囲チェック
        if not self.match_df['match_score'].between(MATCH_SCORE_MIN, MATCH_SCORE_MAX).all():
            logger.error(f"Match scores must be between {MATCH_SCORE_MIN} and {MATCH_SCORE_MAX}")
            return False

        # 金額の妥当性チェック
        if not (self.match_df['amount'] > 0).all():
            logger.error("All amounts must be positive")
            return False

        logger.info("Match suggestions validation passed")
        return True

    def filter_high_confidence_matches(
            self, threshold: float = 0.7) -> pd.DataFrame:
        """高信頼度マッチングの抽出"""
        if self.match_df is None:
            logger.error("Match data not loaded")
            return pd.DataFrame()

        high_confidence = self.match_df[self.match_df['match_score'] >= threshold].copy(
        )

        # 差分比較ログ
        filter_info = {
            '元のマッチング提案件数': len(self.match_df),
            '高信頼度マッチング件数': len(high_confidence),
            '低信頼度マッチング件数': len(self.match_df) - len(high_confidence),
            '閾値': threshold
        }

        if 'amount' in self.match_df.columns:
            filter_info['元の総額'] = self.match_df['amount'].sum()
            filter_info['高信頼度総額'] = high_confidence['amount'].sum()

        if 'match_score' in self.match_df.columns:
            filter_info['元の平均スコア'] = self.match_df['match_score'].mean()
            filter_info['高信頼度平均スコア'] = high_confidence['match_score'].mean()

        log_processing_stage(f"高信頼度マッチング抽出 (閾値: {threshold})", filter_info)

        self.processing_stats['total_suggestions'] = len(self.match_df)
        self.processing_stats['applied_matches'] = len(high_confidence)
        self.processing_stats['rejected_matches'] = len(
            self.match_df) - len(high_confidence)

        logger.info(
            f"High confidence matches (>= {threshold}): {len(high_confidence)} out of {len(self.match_df)}")

        return high_confidence

    def create_journal_entries(
            self,
            high_confidence_matches: pd.DataFrame) -> pd.DataFrame:
        """仕訳エントリの作成"""
        journal_entries = []

        for _, match in high_confidence_matches.iterrows():
            # 入金仕訳（借方：現金、貸方：売掛金）
            journal_entries.append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'transaction_id': match['transaction_id'],
                'project_id': match['project_id'],
                'client_name': match['client_name'],
                'debit_account': '現金',
                'credit_account': '売掛金',
                'amount': match['matched_amount'],
                'description': f"入金消込 - {match['client_name']} ({match['project_id']})",
                'match_score': match['match_score'],
                'entry_type': 'cash_receipt',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            # 売上計上仕訳（借方：売掛金、貸方：売上）
            journal_entries.append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'transaction_id': match['transaction_id'],
                'project_id': match['project_id'],
                'client_name': match['client_name'],
                'debit_account': '売掛金',
                'credit_account': '売上',
                'amount': match['matched_amount'],
                'description': f"売上計上 - {match['client_name']} ({match['project_id']})",
                'match_score': match['match_score'],
                'entry_type': 'revenue_recognition',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        self.journal_df = pd.DataFrame(journal_entries)

        # 統計情報の更新
        self.processing_stats['total_amount'] = high_confidence_matches['amount'].sum(
        )
        self.processing_stats['matched_amount'] = high_confidence_matches['matched_amount'].sum(
        )

        logger.info(f"Created {len(self.journal_df)} journal entries")
        return self.journal_df

    def add_manual_review_entries(
            self, low_confidence_matches: pd.DataFrame) -> pd.DataFrame:
        """手動確認が必要な低信頼度マッチングの追加"""
        manual_review_entries = []

        for _, match in low_confidence_matches.iterrows():
            manual_review_entries.append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'transaction_id': match['transaction_id'],
                'project_id': match['project_id'],
                'client_name': match['client_name'],
                'debit_account': '未決算',
                'credit_account': '未決算',
                'amount': match['amount'],
                'description': f"手動確認要 - {match['client_name']} ({match['project_id']}) - スコア: {match['match_score']:.3f}",
                'match_score': match['match_score'],
                'entry_type': 'manual_review',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        if manual_review_entries:
            manual_df = pd.DataFrame(manual_review_entries)
            self.journal_df = pd.concat(
                [self.journal_df, manual_df], ignore_index=True)
            logger.info(f"Added {len(manual_review_entries)} manual review entries")

        return self.journal_df

    def calculate_journal_statistics(self) -> Dict:
        """仕訳統計の計算"""
        if self.journal_df is None or self.journal_df.empty:
            return {}

        stats = {
            'total_entries': len(self.journal_df),
            'cash_receipt_entries': len(self.journal_df[self.journal_df['entry_type'] == 'cash_receipt']),
            'revenue_entries': len(self.journal_df[self.journal_df['entry_type'] == 'revenue_recognition']),
            'manual_review_entries': len(self.journal_df[self.journal_df['entry_type'] == 'manual_review']),
            'total_debit_amount': self.journal_df[self.journal_df['debit_account'] == '現金']['amount'].sum(),
            'total_credit_amount': self.journal_df[self.journal_df['credit_account'] == '売上']['amount'].sum(),
            'average_match_score': self.journal_df['match_score'].mean()
        }

        logger.info(f"Journal statistics calculated: {stats}")
        return stats

    def save_journal_data(self, output_dir: str) -> str:
        """仕訳データの保存"""
        os.makedirs(output_dir, exist_ok=True)

        # ファイル名の生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"journal_{timestamp}.csv"
        output_path = os.path.join(output_dir, filename)

        # CSVとして保存
        self.journal_df.to_csv(output_path, index=False, encoding='utf-8')

        logger.info(f"Journal data saved: {output_path}")
        return output_path

    def generate_matching_report(self, journal_stats: Dict) -> str:
        """マッチング処理レポートの生成"""
        report = []
        report.append("=" * 60)
        report.append("CASH MATCHING PROCESSING REPORT")
        report.append("=" * 60)
        report.append(f"Processing Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 入力ファイル
        report.append("INPUT FILES:")
        report.append(f"  Match Suggestions: {self.match_suggestion_file}")
        report.append(f"  Bank Data: {self.bank_data_file}")
        report.append(f"  Invoice Seed: {self.invoice_seed_file}")
        report.append("")

        # 処理統計
        report.append("PROCESSING STATISTICS:")
        report.append(f"  Total Suggestions: {self.processing_stats['total_suggestions']}")
        report.append(f"  Applied Matches: {self.processing_stats['applied_matches']}")
        report.append(f"  Rejected Matches: {self.processing_stats['rejected_matches']}")
        report.append(f"  Total Amount: {self.processing_stats['total_amount']:,} yen")
        report.append(f"  Matched Amount: {self.processing_stats['matched_amount']:,} yen")
        report.append("")

        # 仕訳統計
        if journal_stats:
            report.append("JOURNAL STATISTICS:")
            report.append(f"  Total Entries: {journal_stats['total_entries']}")
            report.append(f"  Cash Receipt Entries: {journal_stats['cash_receipt_entries']}")
            report.append(f"  Revenue Entries: {journal_stats['revenue_entries']}")
            report.append(f"  Manual Review Entries: {journal_stats['manual_review_entries']}")
            report.append(f"  Total Debit Amount: {journal_stats['total_debit_amount']:,} yen")
            report.append(f"  Total Credit Amount: {journal_stats['total_credit_amount']:,} yen")
            report.append(f"  Average Match Score: {journal_stats['average_match_score']:.3f}")

        report.append("=" * 60)

        return "\n".join(report)

    def process(self, confidence_threshold: float = 0.7,
                output_dir: str = "output/journal") -> Tuple[pd.DataFrame, str]:
        """メイン処理"""
        logger.info(f"Starting cash matching processing")
        logger.info(f"Confidence threshold: {confidence_threshold}")

        # データ読み込み
        logger.info("=== データ読み込み開始 ===")
        if not self.load_data():
            raise Exception("Failed to load data")

        # マッチング提案の検証
        logger.info("=== マッチング提案検証開始 ===")
        if not self.validate_match_suggestions():
            raise Exception("Match suggestions validation failed")

        # 高信頼度マッチングの抽出
        logger.info("=== 高信頼度マッチング抽出開始 ===")
        high_confidence = self.filter_high_confidence_matches(
            confidence_threshold)

        # 低信頼度マッチングの抽出
        logger.info("=== 低信頼度マッチング抽出開始 ===")
        if self.match_df is None:
            low_confidence = pd.DataFrame()
        else:
            low_confidence = self.match_df[self.match_df['match_score']
                                           < confidence_threshold].copy()

        low_confidence_info = {
            '低信頼度マッチング件数': len(low_confidence)
        }
        if not low_confidence.empty and 'amount' in low_confidence.columns:
            low_confidence_info['低信頼度総額'] = low_confidence['amount'].sum()
        if not low_confidence.empty and 'match_score' in low_confidence.columns:
            low_confidence_info['低信頼度平均スコア'] = low_confidence['match_score'].mean(
            )

        log_processing_stage("低信頼度マッチング抽出", low_confidence_info)

        # 仕訳エントリの作成
        logger.info("=== 仕訳エントリ作成開始 ===")
        self.create_journal_entries(high_confidence)

        journal_info = {
            '作成された仕訳件数': len(
                self.journal_df) if self.journal_df is not None else 0}
        if self.journal_df is not None and 'amount' in self.journal_df.columns:
            journal_info['仕訳総額'] = self.journal_df['amount'].sum()

        log_processing_stage("仕訳エントリ作成", journal_info)

        # 手動確認エントリの追加
        if not low_confidence.empty:
            logger.info("=== 手動確認エントリ追加開始 ===")
            before_manual_count = len(
                self.journal_df) if self.journal_df is not None else 0
            self.add_manual_review_entries(low_confidence)
            after_manual_count = len(
                self.journal_df) if self.journal_df is not None else 0

            manual_info = {
                '追加前仕訳件数': before_manual_count,
                '追加後仕訳件数': after_manual_count,
                '追加された手動確認件数': after_manual_count - before_manual_count
            }
            log_processing_stage("手動確認エントリ追加", manual_info)

        # 統計計算
        logger.info("=== 統計計算開始 ===")
        journal_stats = self.calculate_journal_statistics()

        # 最終統計の差分比較
        if self.journal_df is not None and not self.journal_df.empty:
            final_stats = {
                '総仕訳件数': len(self.journal_df),
                '入金仕訳件数': len(self.journal_df[self.journal_df['entry_type'] == 'cash_receipt']),
                '売上仕訳件数': len(self.journal_df[self.journal_df['entry_type'] == 'revenue_recognition']),
                '手動確認件数': len(self.journal_df[self.journal_df['entry_type'] == 'manual_review'])
            }

            if 'amount' in self.journal_df.columns:
                final_stats['総仕訳金額'] = self.journal_df['amount'].sum()
                final_stats['入金仕訳金額'] = self.journal_df[self.journal_df['debit_account']
                                                        == '現金']['amount'].sum()
                final_stats['売上仕訳金額'] = self.journal_df[self.journal_df['credit_account']
                                                        == '売上']['amount'].sum()

            if 'match_score' in self.journal_df.columns:
                final_stats['平均マッチスコア'] = self.journal_df['match_score'].mean()
        else:
            final_stats = {
                '総仕訳件数': 0,
                '入金仕訳件数': 0,
                '売上仕訳件数': 0,
                '手動確認件数': 0
            }

        log_processing_stage("最終統計", final_stats)

        # データ保存
        output_path = self.save_journal_data(output_dir)

        # レポート生成・保存
        report = self.generate_matching_report(journal_stats)
        report_dir = "output/reports"
        os.makedirs(report_dir, exist_ok=True)

        report_filename = f"cash_matching_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = os.path.join(report_dir, report_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Matching report saved: {report_path}")

        return self.journal_df if self.journal_df is not None else pd.DataFrame(), output_path


def main():
    """メイン処理"""
    import glob
    import traceback

    # 最新のマッチング提案ファイルを検索
    match_files = glob.glob("output/ai_output/match_suggestion_*.csv")
    if not match_files:
        logger.error("No match suggestion files found")
        print("[ERROR] No match suggestion files found")
        return
    match_file = sorted(match_files)[-1]

    # 最新の銀行データファイルを検索
    bank_files = glob.glob("output/bank_processing/processed_bank_txn_*.csv")
    if not bank_files:
        logger.error("No processed bank data files found")
        print("[ERROR] No processed bank data files found")
        return
    bank_file = sorted(bank_files)[-1]

    # 最新の請求書シードファイルを検索
    seed_files = glob.glob("output/seed/invoice_seed_*.csv")
    if not seed_files:
        logger.error("No invoice seed files found")
        print("[ERROR] No invoice seed files found")
        return
    seed_file = sorted(seed_files)[-1]

    # 処理実行
    processor = CashMatchingProcessor(match_file, bank_file, seed_file)

    try:
        journal_df, output_path = processor.process(confidence_threshold=0.7)

        print("[OK] Cash matching processing completed")
        print(f"\U0001F4C1 Output file: {output_path}")
        print(f"\U0001F4CA Created {len(journal_df)} journal entries")
        print(
            f"\U0001F4B0 Total matched amount: {processor.processing_stats['matched_amount']:,} yen")

    except Exception as e:
        error_msg = f"[ERROR] Cash matching processing failed: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(error_msg)
        print(traceback.format_exc())
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
