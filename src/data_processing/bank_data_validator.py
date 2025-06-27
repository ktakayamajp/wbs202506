"""
bank_data_validator.py

銀行取引データ（CSV）の検証・バリデーションを行うモジュール。
必須カラム・データ型・範囲・重複・整合性などをチェックし、
会計処理やAIマッチングの前処理として利用。
"""
import pandas as pd
import os
from datetime import datetime
from typing import Dict
from utils.logger import logger
from config.constants import (
    AMOUNT_SMALL_MAX, AMOUNT_MEDIUM_MAX, CONFIDENCE_THRESHOLD_DEFAULT,
    MATCH_SCORE_MIN, MATCH_SCORE_MAX, YEAR_MIN, YEAR_MAX, MONTH_MIN, MONTH_MAX,
    OUTLIER_STDDEV, INVOICE_MONTHLY_LIMIT
)
from utils.data_utils import check_file_exists, read_csv_with_log, check_required_columns, find_duplicates, detect_outliers


class BankDataValidator:
    """
    銀行データ（CSV）の検証・バリデーションを行うクラス。

    Attributes:
        file_path (str): 入力ファイルパス
        df (pd.DataFrame): 銀行データ
        validation_results (dict): 検証結果・エラー・警告など
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.validation_results = {
            'file_exists': False,
            'file_readable': False,
            'required_columns': False,
            'data_types': False,
            'data_ranges': False,
            'duplicates': False,
            'matching_consistency': False,
            'amount_consistency': False,
            'date_consistency': False,
            'total_transactions': 0,
            'total_amount': 0,
            'matched_amount': 0,
            'errors': [],
            'warnings': []
        }

    def validate_file_exists(self) -> bool:
        """ファイルの存在確認（共通関数利用）"""
        exists = check_file_exists(self.file_path)
        self.validation_results['file_exists'] = exists
        return exists

    def validate_file_readable(self) -> bool:
        """ファイルの読み込み確認（共通関数利用）"""
        self.df = read_csv_with_log(self.file_path)
        readable = self.df is not None
        self.validation_results['file_readable'] = readable
        return readable

    def validate_required_columns(self) -> bool:
        """必須カラムの存在確認（共通関数利用）"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        required_columns = [
            'Transaction_Date', 'Client_Name', 'Amount', 'Transaction_Type',
            'processed_at', 'transaction_id', 'year', 'month', 'amount_category',
            'matching_status', 'matching_confidence'
        ]
        missing_columns = check_required_columns(self.df, required_columns)
        if not missing_columns:
            self.validation_results['required_columns'] = True
            return True
        else:
            self.validation_results['errors'].append(f"Missing required columns: {missing_columns}")
            return False

    def validate_data_types(self) -> bool:
        """データ型の検証"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        errors = []

        # Transaction_Date: 日付型
        try:
            self.df['Transaction_Date'] = pd.to_datetime(
                self.df['Transaction_Date'])
        except Exception as e:
            errors.append(f"Transaction_Date format invalid: {e}")

        # Amount: 数値型で正の値
        if not pd.api.types.is_numeric_dtype(self.df['Amount']):
            errors.append("Amount must be numeric")
        elif not (self.df['Amount'] > 0).all():
            errors.append("Amount must be positive")

        # Transaction_Type: 入金のみ
        if not (self.df['Transaction_Type'] == '入金').all():
            errors.append("All transactions must be '入金' type")

        # transaction_id: 文字列でTXN_で始まる
        if not self.df['transaction_id'].str.match(r'^TXN_\d{8}_\d{4}$').all():
            errors.append(
                "transaction_id format invalid (should be TXN_YYYYMMDD_XXXX)")

        # year, month: 数値で妥当な範囲
        if not self.df['year'].between(YEAR_MIN, YEAR_MAX).all():
            errors.append(f"year out of valid range ({YEAR_MIN}-{YEAR_MAX})")
        if not self.df['month'].between(MONTH_MIN, MONTH_MAX).all():
            errors.append(f"month out of valid range ({MONTH_MIN}-{MONTH_MAX})")

        # matching_confidence: 0-1の範囲
        if not self.df['matching_confidence'].between(MATCH_SCORE_MIN, MATCH_SCORE_MAX).all():
            errors.append(f"matching_confidence out of valid range ({MATCH_SCORE_MIN}-{MATCH_SCORE_MAX})")

        if not errors:
            self.validation_results['data_types'] = True
            logger.info("Data types validation passed")
            return True
        else:
            for error in errors:
                self.validation_results['errors'].append(error)
            logger.error(f"Data types validation failed: {errors}")
            return False

    def validate_data_ranges(self) -> bool:
        """データ範囲の検証（外れ値検出を共通関数利用）"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        warnings = []
        # 金額の異常値チェック
        outliers = detect_outliers(self.df, 'Amount', OUTLIER_STDDEV)
        if not outliers.empty:
            for _, row in outliers.iterrows():
                warning_msg = f"Outlier amount: {row['transaction_id']} = {row['Amount']:,} yen"
                warnings.append(warning_msg)

        # マッチング信頼度の低い取引を警告
        low_confidence = self.df[
            (self.df['matching_status'] == 'matched') &
            (self.df['matching_confidence'] < CONFIDENCE_THRESHOLD_DEFAULT)
        ]

        if not low_confidence.empty:
            for _, row in low_confidence.iterrows():
                warning_msg = (
                    f"Low confidence match: {row['transaction_id']} = {row['matching_confidence']:.3f}")
                warnings.append(warning_msg)

        # 日付の妥当性チェック（未来日付を警告）
        future_dates = self.df[self.df['Transaction_Date'] > datetime.now()]
        if not future_dates.empty:
            warning_msg = f"Future transaction dates found: {len(future_dates)} transactions"
            warnings.append(warning_msg)

        if not warnings:
            self.validation_results['data_ranges'] = True
            logger.info("Data ranges validation passed")
        else:
            self.validation_results['warnings'].extend(warnings)
            logger.warning(f"Data ranges validation warnings: {warnings}")

        return True

    def validate_duplicates(self) -> bool:
        """重複データの検証（共通関数利用）"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        # transaction_idの重複チェック
        duplicate_ids = find_duplicates(self.df, ['transaction_id'])
        if not duplicate_ids.empty:
            error_msg = f"Duplicate transaction_ids found: {duplicate_ids['transaction_id'].tolist()}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        # 同じ日付・クライアント・金額の重複チェック
        duplicate_transactions = find_duplicates(self.df, ['Transaction_Date', 'Client_Name', 'Amount'])
        if not duplicate_transactions.empty:
            warning_msg = f"Potential duplicate transactions found: {len(duplicate_transactions)} rows"
            self.validation_results['warnings'].append(warning_msg)
            logger.warning(warning_msg)
        self.validation_results['duplicates'] = True
        logger.info("Duplicate validation passed")
        return True

    def validate_matching_consistency(self) -> bool:
        """マッチング結果の整合性確認"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        errors = []
        warnings = []

        # マッチングステータスの妥当性
        valid_statuses = [
            'matched',
            'unmatched',
            'matching_error',
            'no_ar_data']
        invalid_statuses = self.df[~self.df['matching_status'].isin(
            valid_statuses)]

        if not invalid_statuses.empty:
            unique_statuses = pd.Series(invalid_statuses['matching_status'])
            unique_list = unique_statuses.unique().tolist()
            error_msg = f"Invalid matching_status values: {unique_list}"
            errors.append(error_msg)

        # マッチング信頼度の整合性
        # matchedステータスで信頼度が0のもの
        inconsistent_matched = self.df[
            (self.df['matching_status'] == 'matched') &
            (self.df['matching_confidence'] == 0)
        ]

        if not inconsistent_matched.empty:
            warning_msg = f"Matched transactions with zero confidence: {len(inconsistent_matched)}"
            warnings.append(warning_msg)

        # unmatchedステータスで信頼度が高いもの
        inconsistent_unmatched = self.df[
            (self.df['matching_status'] == 'unmatched') &
            (self.df['matching_confidence'] > 0.5)
        ]

        if not inconsistent_unmatched.empty:
            warning_msg = f"Unmatched transactions with high confidence: {len(inconsistent_unmatched)}"
            warnings.append(warning_msg)

        if not errors:
            self.validation_results['matching_consistency'] = True
            logger.info("Matching consistency validation passed")
        else:
            for error in errors:
                self.validation_results['errors'].append(error)
            logger.error(f"Matching consistency validation failed: {errors}")

        if warnings:
            self.validation_results['warnings'].extend(warnings)
            logger.warning(f"Matching consistency warnings: {warnings}")

        return len(errors) == 0

    def validate_amount_consistency(self) -> bool:
        """金額の整合性確認"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        warnings = []

        # 同じ取引IDで異なる金額がある場合
        amount_variations = self.df.groupby('transaction_id')[
            'Amount'].nunique()
        inconsistent_amounts = amount_variations[amount_variations > 1]

        if len(inconsistent_amounts) > 0:
            inconsistent_amounts_index = list(pd.Series(inconsistent_amounts).index)
            warning_msg = (
                f"Amount variations for same transaction_id: {inconsistent_amounts_index}")
            warnings.append(warning_msg)

        # 金額カテゴリの妥当性
        amount_categories = self.df.groupby('amount_category')['Amount'].agg(['min', 'max', 'count'])

        # カテゴリ境界の確認
        if 'small' in amount_categories.index:
            if amount_categories.loc['small', 'max'] >= 100000:
                warning_msg = "Small category contains amounts >= 100,000 yen"
                warnings.append(warning_msg)

        if 'medium' in amount_categories.index:
            if (amount_categories.loc['medium', 'min'] < AMOUNT_SMALL_MAX or 
                amount_categories.loc['medium', 'max'] >= AMOUNT_MEDIUM_MAX):
                warning_msg = f"Medium category contains amounts outside {AMOUNT_SMALL_MAX:,}-{AMOUNT_MEDIUM_MAX:,} range"
                warnings.append(warning_msg)

        if 'large' in amount_categories.index:
            if amount_categories.loc['large', 'min'] < AMOUNT_MEDIUM_MAX:
                warning_msg = f"Large category contains amounts < {AMOUNT_MEDIUM_MAX:,} yen"
                warnings.append(warning_msg)

        if not warnings:
            self.validation_results['amount_consistency'] = True
            logger.info("Amount consistency validation passed")
        else:
            self.validation_results['warnings'].extend(warnings)
            logger.warning(f"Amount consistency warnings: {warnings}")

        return True

    def validate_date_consistency(self) -> bool:
        """日付の整合性確認"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        warnings = []

        # year, monthとTransaction_Dateの整合性
        self.df['extracted_year'] = self.df['Transaction_Date'].dt.year
        self.df['extracted_month'] = self.df['Transaction_Date'].dt.month

        inconsistent_dates = self.df[
            (self.df['year'] != self.df['extracted_year']) |
            (self.df['month'] != self.df['extracted_month'])
        ]

        if not inconsistent_dates.empty:
            warning_msg = f"Date inconsistency found: {len(inconsistent_dates)} rows"
            warnings.append(warning_msg)

        # 処理日時の妥当性
        self.df['processed_datetime'] = pd.to_datetime(self.df['processed_at'])
        future_processing = self.df[self.df['processed_datetime']
                                    > datetime.now()]

        if not future_processing.empty:
            warning_msg = f"Future processing timestamps found: {len(future_processing)} rows"
            warnings.append(warning_msg)

        # 日付の順序性（取引日が処理日より後）
        invalid_order = self.df[self.df['Transaction_Date']
                                > self.df['processed_datetime']]

        if not invalid_order.empty:
            warning_msg = f"Transaction date after processing date: {len(invalid_order)} rows"
            warnings.append(warning_msg)

        if not warnings:
            self.validation_results['date_consistency'] = True
            logger.info("Date consistency validation passed")
        else:
            self.validation_results['warnings'].extend(warnings)
            logger.warning(f"Date consistency warnings: {warnings}")

        return True

    def calculate_summary(self):
        """サマリー情報の計算"""
        if self.df is not None:
            self.validation_results['total_transactions'] = len(self.df)
            self.validation_results['total_amount'] = self.df['Amount'].sum()
            self.validation_results['matched_amount'] = self.df[
                self.df['matching_status'] == 'matched'
            ]['Amount'].sum()

            logger.info(
                f"Summary: {self.validation_results['total_transactions']} transactions, " f"Total amount: {self.validation_results['total_amount']:,} yen"
            )

    def run_all_validations(self) -> Dict:
        """全検証を実行"""
        logger.info(f"Starting bank data validation for: {self.file_path}")

        # 基本検証
        if not self.validate_file_exists():
            return self.validation_results

        if not self.validate_file_readable():
            return self.validation_results

        # データ検証
        self.validate_required_columns()
        if not self.validation_results['required_columns']:
            # 必須カラムが不足している場合は以降のバリデーションをスキップ
            return self.validation_results

        self.validate_data_types()
        self.validate_data_ranges()
        self.validate_duplicates()
        self.validate_matching_consistency()
        self.validate_amount_consistency()
        self.validate_date_consistency()

        # サマリー計算
        self.calculate_summary()

        # 結果判定
        is_valid = (
            self.validation_results['file_exists'] and
            self.validation_results['file_readable'] and
            self.validation_results['required_columns'] and
            self.validation_results['data_types'] and
            self.validation_results['duplicates'] and
            self.validation_results['matching_consistency']
        )

        if is_valid:
            logger.info("✅ Bank data validation PASSED")
        else:
            logger.error("❌ Bank data validation FAILED")

        return self.validation_results

    def generate_report(self) -> str:
        """検証レポートの生成"""
        report = []
        report.append("=" * 60)
        report.append("BANK DATA VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"File: {self.file_path}")
        report.append(
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # サマリー
        report.append("SUMMARY:")
        report.append(
            f"  Total Transactions: {self.validation_results['total_transactions']}")
        report.append(
            f"  Total Amount: {self.validation_results['total_amount']:,} yen")
        report.append(
            f"  Matched Amount: {self.validation_results['matched_amount']:,} yen")
        report.append("")

        # 検証結果
        report.append("VALIDATION RESULTS:")
        for key, value in self.validation_results.items():
            if key in [
                'errors',
                'warnings',
                'total_amount',
                'total_transactions',
                    'matched_amount']:
                continue
            status = "✅ PASS" if value else "❌ FAIL"
            report.append(f"  {key}: {status}")

        # エラー
        if self.validation_results['errors']:
            report.append("")
            report.append("ERRORS:")
            for error in self.validation_results['errors']:
                report.append(f"  ❌ {error}")

        # 警告
        if self.validation_results['warnings']:
            report.append("")
            report.append("WARNINGS:")
            for warning in self.validation_results['warnings']:
                report.append(f"  ⚠️  {warning}")

        report.append("=" * 60)

        return "\n".join(report)


def main():
    """メイン処理"""
    import traceback
    try:
        # 最新の処理済み銀行データファイルを検索
        bank_dir = "output/bank_processing"
        if not os.path.exists(bank_dir):
            logger.error(f"Bank processing directory not found: {bank_dir}")
            print(f"[ERROR] Bank processing directory not found: {bank_dir}")
            return

        bank_files = [f for f in os.listdir(bank_dir) if f.startswith(
            'processed_bank_txn_') and f.endswith('.csv')]

        if not bank_files:
            logger.error("No processed bank data files found")
            print("[ERROR] No processed bank data files found")
            return

        # 最新のファイルを選択
        latest_file = sorted(bank_files)[-1]
        file_path = os.path.join(bank_dir, latest_file)

        # 検証実行
        validator = BankDataValidator(file_path)
        results = validator.run_all_validations()

        # レポート生成・出力
        report = validator.generate_report()
        print(report)

        # レポートファイル保存
        report_dir = "output/reports"
        os.makedirs(report_dir, exist_ok=True)

        report_filename = f"bank_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = os.path.join(report_dir, report_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Validation report saved: {report_path}")

        # 検証結果に基づく終了コード
        if results['errors']:
            exit(1)
        else:
            exit(0)
    except Exception as e:
        error_msg = f"[ERROR] Bank data validation failed: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(error_msg)
        print(traceback.format_exc())
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
