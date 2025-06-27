"""
prep_bank_txn.py

銀行明細データ（CSV）の前処理・検証・整形を行うモジュール。
AIマッチングや会計処理のためのデータクレンジング・構造化を担う。
"""
import pandas as pd
import os
from datetime import datetime
from typing import Dict, Tuple
from utils.logger import logger
from config.constants import AMOUNT_SMALL_MAX, AMOUNT_MEDIUM_MAX


class BankTransactionProcessor:
    """
    銀行明細CSVの前処理・検証・整形を行うクラス。

    Attributes:
        input_file (str): 入力ファイルパス
        df (pd.DataFrame): 元データ
        processed_df (pd.DataFrame): 前処理済みデータ
        processing_stats (dict): 処理統計
    """

    def __init__(self, input_file: str):
        self.input_file = input_file
        self.df = None
        self.processed_df = None
        self.processing_stats = {
            'total_transactions': 0,
            'valid_transactions': 0,
            'invalid_transactions': 0,
            'total_amount': 0,
            'processed_amount': 0
        }

    def load_bank_data(self) -> bool:
        """銀行データの読み込み"""
        try:
            self.df = pd.read_csv(self.input_file, encoding='utf-8')
            self.processing_stats['total_transactions'] = len(self.df)
            logger.info(
                f"Loaded {len(self.df)} bank transactions from {self.input_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load bank data: {e}")
            return False

    def validate_data_structure(self) -> bool:
        """データ構造の検証"""
        required_columns = [
            'Transaction_Date',
            'Client_Name',
            'Amount',
            'Transaction_Type']
        missing_columns = [
            col for col in required_columns if col not in self.df.columns]

        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False

        logger.info("Data structure validation passed")
        return True

    def clean_transaction_data(self) -> pd.DataFrame:
        """取引データのクリーニング"""
        # データのコピーを作成
        cleaned_df = self.df.copy()

        # 日付の正規化
        cleaned_df['Transaction_Date'] = pd.to_datetime(
            cleaned_df['Transaction_Date'])

        # 金額の正規化（数値型に変換）
        cleaned_df['Amount'] = pd.to_numeric(
            cleaned_df['Amount'], errors='coerce')

        # 取引タイプの正規化
        cleaned_df['Transaction_Type'] = cleaned_df['Transaction_Type'].str.strip()

        # クライアント名の正規化
        cleaned_df['Client_Name'] = cleaned_df['Client_Name'].str.strip()

        # 無効なデータを除外
        initial_count = len(cleaned_df)
        cleaned_df = cleaned_df.dropna(
            subset=[
                'Transaction_Date',
                'Client_Name',
                'Amount'])

        # 入金取引のみを抽出
        cleaned_df = cleaned_df[cleaned_df['Transaction_Type'] == '入金']

        # 金額が正の値のみを抽出
        cleaned_df = cleaned_df[cleaned_df['Amount'] > 0]

        final_count = len(cleaned_df)
        self.processing_stats['valid_transactions'] = final_count
        self.processing_stats['invalid_transactions'] = initial_count - final_count

        logger.info(
            f"Cleaned data: {initial_count} -> {final_count} valid transactions")

        return cleaned_df

    def add_processing_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """処理メタデータの追加"""
        # 処理日時を追加
        df['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 取引IDを生成（カラムがなければ自動生成）
        def make_txn_id(row):
            txn_part = row['transaction_id'] if 'transaction_id' in row and pd.notnull(row['transaction_id']) else row.name
            proj_part = row['project_id'] if 'project_id' in row and pd.notnull(row['project_id']) else row.get('Client_Name', '')
            return f"TXN_{txn_part}_{proj_part}"
        df['transaction_id'] = df.apply(make_txn_id, axis=1)

        # 年月を追加（マッチング用）
        df['year'] = pd.to_datetime(df['Transaction_Date']).dt.year
        df['month'] = pd.to_datetime(df['Transaction_Date']).dt.month

        # 金額の範囲分類
        df['amount_category'] = df['Amount'].apply(self._categorize_amount)

        logger.info("Added processing metadata")
        return df

    def _categorize_amount(self, amount: float) -> str:
        """金額の範囲分類"""
        if amount < AMOUNT_SMALL_MAX:
            return 'small'
        elif amount < AMOUNT_MEDIUM_MAX:
            return 'medium'
        else:
            return 'large'

    def match_with_accounts_receivable(self, df: pd.DataFrame) -> pd.DataFrame:
        """売掛金データとの照合"""
        try:
            # 売掛金データの読み込み
            ar_file = "data/Updated_Accounts_Receivable.csv"
            if os.path.exists(ar_file):
                ar_df = pd.read_csv(ar_file)

                # クライアント名で照合
                merged_df = pd.merge(
                    df,
                    ar_df[['Project_ID', 'Client', 'AR_Amount']],
                    left_on='Client_Name',
                    right_on='Client',
                    how='left'
                )

                # 金額の近さでフィルタリング（±10%の範囲）
                merged_df['amount_diff_pct'] = abs(
                    (merged_df['Amount'] - merged_df['AR_Amount']) / merged_df['AR_Amount'])

                # 金額が近い取引のみを抽出
                matched_df = merged_df[merged_df['amount_diff_pct'] <= 0.1].copy(
                )

                # マッチング結果を記録
                matched_df['matching_status'] = 'matched'
                matched_df['matching_confidence'] = 1 - \
                    matched_df['amount_diff_pct']

                # マッチしなかった取引も含める
                unmatched_df = merged_df[merged_df['amount_diff_pct'] > 0.1].copy(
                )
                unmatched_df['matching_status'] = 'unmatched'
                unmatched_df['matching_confidence'] = 0.0

                # 結果を結合
                final_df = pd.concat(
                    [matched_df, unmatched_df], ignore_index=True)

                logger.info(f"AR matching: {len(matched_df)} matches found")
                return final_df
            else:
                logger.warning(
                    "Accounts receivable file not found, skipping matching")
                df['matching_status'] = 'no_ar_data'
                df['matching_confidence'] = 0.0
                return df

        except Exception as e:
            logger.error(f"AR matching failed: {e}")
            df['matching_status'] = 'matching_error'
            df['matching_confidence'] = 0.0
            return df

    def calculate_statistics(self, df: pd.DataFrame):
        """統計情報の計算"""
        self.processing_stats['total_amount'] = df['Amount'].sum()
        self.processing_stats['processed_amount'] = df[df['matching_status']
                                                       == 'matched']['Amount'].sum()

        # 日別集計
        daily_stats = df.groupby('Transaction_Date').agg({
            'Amount': ['sum', 'count'],
            'matching_status': lambda x: (x == 'matched').sum()
        }).round(2)

        # クライアント別集計
        client_stats = df.groupby('Client_Name').agg({
            'Amount': ['sum', 'count'],
            'matching_status': lambda x: (x == 'matched').sum()
        }).round(2)

        logger.info(f"Processing statistics calculated")
        logger.info(f"Total amount: {self.processing_stats['total_amount']:,} yen")
        logger.info(f"Matched amount: {self.processing_stats['processed_amount']:,} yen")

        return daily_stats, client_stats

    def save_processed_data(self, df: pd.DataFrame, output_dir: str) -> str:
        """処理済みデータの保存"""
        os.makedirs(output_dir, exist_ok=True)

        # ファイル名の生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"processed_bank_txn_{timestamp}.csv"
        output_path = os.path.join(output_dir, filename)

        # CSVとして保存
        df.to_csv(output_path, index=False, encoding='utf-8')

        logger.info(f"Processed data saved: {output_path}")
        return output_path

    def generate_processing_report(
            self,
            daily_stats: pd.DataFrame,
            client_stats: pd.DataFrame) -> str:
        """処理レポートの生成"""
        report = []
        report.append("=" * 60)
        report.append("BANK TRANSACTION PROCESSING REPORT")
        report.append("=" * 60)
        report.append(f"Input File: {self.input_file}")
        report.append(
            f"Processing Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 処理統計
        report.append("PROCESSING STATISTICS:")
        report.append(
            f"  Total Transactions: {self.processing_stats['total_transactions']}")
        report.append(
            f"  Valid Transactions: {self.processing_stats['valid_transactions']}")
        report.append(
            f"  Invalid Transactions: {self.processing_stats['invalid_transactions']}")
        report.append(
            f"  Total Amount: {self.processing_stats['total_amount']:,} yen")
        report.append(
            f"  Matched Amount: {self.processing_stats['processed_amount']:,} yen")
        report.append("")

        # 日別統計
        report.append("DAILY STATISTICS:")
        for date, row in daily_stats.iterrows():
            report.append(
                f"  {date.strftime('%Y-%m-%d')}: {row[('Amount', 'sum')]:,} yen ({row[('Amount', 'count')]} txn, {row[('matching_status', '<lambda>')]} matched)")
        report.append("")

        # クライアント別統計
        report.append("CLIENT STATISTICS:")
        for client, row in client_stats.iterrows():
            report.append(
                f"  {client}: {row[('Amount', 'sum')]:,} yen ({row[('Amount', 'count')]} txn, {row[('matching_status', '<lambda>')]} matched)")

        report.append("=" * 60)

        return "\n".join(report)

    def process(
            self, output_dir: str = "output/bank_processing") -> Tuple[pd.DataFrame, str]:
        """メイン処理"""
        logger.info(f"Starting bank transaction processing: {self.input_file}")

        # データ読み込み
        if not self.load_bank_data():
            raise Exception("Failed to load bank data")

        # データ構造検証
        if not self.validate_data_structure():
            raise Exception("Data structure validation failed")

        # データクリーニング
        cleaned_df = self.clean_transaction_data()

        # メタデータ追加
        processed_df = self.add_processing_metadata(cleaned_df)

        # 売掛金との照合
        final_df = self.match_with_accounts_receivable(processed_df)

        # 統計計算
        daily_stats, client_stats = self.calculate_statistics(final_df)

        # データ保存
        output_path = self.save_processed_data(final_df, output_dir)

        # レポート生成・保存
        report = self.generate_processing_report(daily_stats, client_stats)
        report_dir = "output/reports"
        os.makedirs(report_dir, exist_ok=True)

        report_filename = f"bank_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = os.path.join(report_dir, report_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Processing report saved: {report_path}")

        return final_df, output_path


def main():
    """メイン処理"""
    # 入力ファイルの指定
    input_file = "data/03_Bank_Data_Final.csv"

    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return

    # 処理実行
    processor = BankTransactionProcessor(input_file)

    try:
        processed_df, output_path = processor.process()

        print(f"[INFO] Output file: {output_path}")
        print(f"[INFO] Processed {len(processed_df)} transactions")
        print(f"[INFO] Total amount: {processed_df['Amount'].sum():,} yen")

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        print(f"[ERROR] Processing failed: {e}")


if __name__ == "__main__":
    main()
