import pandas as pd
import os
from datetime import datetime
from typing import Dict
from utils.logger import logger
from config.constants import MATCH_SCORE_MIN, MATCH_SCORE_MAX, AMOUNT_TOLERANCE, OUTLIER_STDDEV


class MatchingValidator:
    """
    仕訳データ（journal）とマッチング提案データ（match_suggestion）の
    整合性・会計バランス・重複・データ型などを検証するクラス。

    Attributes:
        journal_file (str): 仕訳データCSVファイルパス
        match_suggestion_file (str): マッチング提案CSVファイルパス
        journal_df (pd.DataFrame): 仕訳データ
        match_df (pd.DataFrame): マッチング提案データ
        validation_results (dict): 検証結果・エラー・警告など
    """

    def __init__(self, journal_file: str, match_suggestion_file: str):
        self.journal_file = journal_file
        self.match_suggestion_file = match_suggestion_file
        self.journal_df = None
        self.match_df = None
        self.validation_results = {
            'file_exists': False,
            'file_readable': False,
            'required_columns': False,
            'data_types': False,
            'accounting_balance': False,
            'matching_consistency': False,
            'amount_consistency': False,
            'duplicate_entries': False,
            'total_entries': 0,
            'total_debit': 0,
            'total_credit': 0,
            'errors': [],
            'warnings': []
        }

    def validate_file_exists(self) -> bool:
        """ファイルの存在確認"""
        if os.path.exists(self.journal_file):
            self.validation_results['file_exists'] = True
            logger.info(f"Journal file exists: {self.journal_file}")
        else:
            error_msg = f"Journal file not found: {self.journal_file}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        if os.path.exists(self.match_suggestion_file):
            logger.info(f"Match suggestion file exists: {self.match_suggestion_file}")
        else:
            logger.warning(f"Match suggestion file does not exist: {self.match_suggestion_file}")

        return True

    def validate_file_readable(self) -> bool:
        """ファイルの読み込み確認"""
        try:
            self.journal_df = pd.read_csv(self.journal_file, encoding='utf-8')
            self.validation_results['file_readable'] = True
            logger.info(
                f"Journal file readable: {len(self.journal_df)} rows loaded")

            self.match_df = pd.read_csv(
                self.match_suggestion_file, encoding='utf-8')
            logger.info(
                f"Match suggestion file readable: {len(self.match_df)} rows loaded")

            return True
        except Exception as e:
            error_msg = f"File not readable: {e}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

    def validate_required_columns(self) -> bool:
        """必須カラムの存在確認"""
        if self.journal_df is None or self.match_df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        # 仕訳ファイルの必須カラム
        journal_required = [
            'date', 'transaction_id', 'project_id', 'client_name',
            'debit_account', 'credit_account', 'amount', 'description',
            'match_score', 'entry_type', 'created_at'
        ]

        missing_journal_columns = [
            col for col in journal_required if col not in self.journal_df.columns]

        if missing_journal_columns:
            error_msg = f"Missing required columns in journal: {missing_journal_columns}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        # マッチング提案ファイルの必須カラム
        match_required = [
            'transaction_id', 'project_id', 'client_name', 'amount',
            'matched_amount', 'match_score'
        ]

        missing_match_columns = [
            col for col in match_required if col not in self.match_df.columns]

        if missing_match_columns:
            error_msg = f"Missing required columns in match suggestions: {missing_match_columns}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        self.validation_results['required_columns'] = True
        logger.info("All required columns present")
        return True

    def validate_data_types(self) -> bool:
        """データ型の検証"""
        errors = []

        # 日付形式の検証
        try:
            self.journal_df['date'] = pd.to_datetime(self.journal_df['date'])
            self.journal_df['created_at'] = pd.to_datetime(
                self.journal_df['created_at'])
        except Exception as e:
            errors.append(f"Date format invalid: {e}")

        # 金額の数値型検証
        if not pd.api.types.is_numeric_dtype(self.journal_df['amount']):
            errors.append("Journal amount must be numeric")
        elif not (self.journal_df['amount'] > 0).all():
            errors.append("Journal amount must be positive")

        if not pd.api.types.is_numeric_dtype(self.match_df['amount']):
            errors.append("Match suggestion amount must be numeric")
        elif not (self.match_df['amount'] > 0).all():
            errors.append("Match suggestion amount must be positive")

        # マッチングスコアの範囲検証
        if not self.journal_df['match_score'].between(MATCH_SCORE_MIN, MATCH_SCORE_MAX).all():
            errors.append(f"Match score out of valid range ({MATCH_SCORE_MIN}-{MATCH_SCORE_MAX})")

        if not self.match_df['match_score'].between(MATCH_SCORE_MIN, MATCH_SCORE_MAX).all():
            errors.append(f"Match suggestion score out of valid range ({MATCH_SCORE_MIN}-{MATCH_SCORE_MAX})")

        # エントリタイプの妥当性
        valid_entry_types = [
            'cash_receipt',
            'revenue_recognition',
            'manual_review']
        invalid_types = self.journal_df[~self.journal_df['entry_type'].isin(
            valid_entry_types)]

        if not invalid_types.empty:
            errors.append(
                f"Invalid entry types: {invalid_types['entry_type'].unique().tolist()}")

        if not errors:
            self.validation_results['data_types'] = True
            logger.info("Data types validation passed")
            return True
        else:
            for error in errors:
                self.validation_results['errors'].append(error)
            logger.error(f"Data types validation failed: {errors}")
            return False

    def validate_accounting_balance(self) -> bool:
        """会計バランスの検証"""
        if self.journal_df is None:
            error_msg = "Journal DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        warnings = []

        # 借方・貸方の合計金額計算
        debit_total = self.journal_df[self.journal_df['debit_account'] == '現金']['amount'].sum(
        )
        credit_total = self.journal_df[self.journal_df['credit_account'] == '売上']['amount'].sum(
        )

        self.validation_results['total_debit'] = debit_total
        self.validation_results['total_credit'] = credit_total

        # バランスチェック（現金と売上の金額が一致するはず）
        if abs(debit_total - credit_total) > 1:  # 1円以下の誤差は許容
            error_msg = f"Accounting balance mismatch: Debit={debit_total}, Credit={credit_total}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        # 各取引IDごとのバランスチェック
        for transaction_id in self.journal_df['transaction_id'].unique():
            txn_entries = self.journal_df[self.journal_df['transaction_id']
                                          == transaction_id]

            # 入金仕訳と売上仕訳のペアチェック
            cash_entries = txn_entries[txn_entries['entry_type']
                                       == 'cash_receipt']
            revenue_entries = txn_entries[txn_entries['entry_type']
                                          == 'revenue_recognition']

            if len(cash_entries) != len(revenue_entries):
                warning_msg = f"Unbalanced entries for {transaction_id}: {len(txn_entries)} entries"
                warnings.append(warning_msg)

            # 同じ取引ID内での金額一致チェック
            cash_amount = cash_entries['amount'].sum()
            revenue_amount = revenue_entries['amount'].sum()

            if abs(cash_amount - revenue_amount) > AMOUNT_TOLERANCE:
                warning_msg = f"Inconsistent amounts for {transaction_id}: Cash={cash_amount:,}, Revenue={revenue_amount:,}"
                warnings.append(warning_msg)

        if not warnings:
            self.validation_results['accounting_balance'] = True
            logger.info("Accounting balance validation passed")
        else:
            self.validation_results['warnings'].extend(warnings)
            logger.warning(f"Accounting balance warnings: {warnings}")

        return True

    def validate_matching_consistency(self) -> bool:
        """マッチング整合性の検証"""
        if self.journal_df is None or self.match_df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        errors = []
        warnings = []

        # 仕訳とマッチング提案の整合性チェック
        journal_transactions = set(self.journal_df['transaction_id'].unique())
        match_transactions = set(self.match_df['transaction_id'].unique())

        # 仕訳にあるがマッチング提案にない取引
        missing_in_match = journal_transactions - match_transactions
        if missing_in_match:
            warning_msg = f"Transactions in journal but not in match suggestions: {missing_in_match}"
            warnings.append(warning_msg)

        # マッチング提案にあるが仕訳にない取引
        missing_in_journal = match_transactions - journal_transactions
        if missing_in_journal:
            warning_msg = f"Transactions in match suggestions but not in journal: {missing_in_journal}"
            warnings.append(warning_msg)

        # 共通の取引IDでの金額・スコア整合性チェック
        common_transactions = journal_transactions & match_transactions

        for txn_id in common_transactions:
            journal_txn = self.journal_df[self.journal_df['transaction_id'] == txn_id]
            match_txn = self.match_df[self.match_df['transaction_id'] == txn_id]

            # 金額の整合性
            journal_amount = journal_txn[journal_txn['entry_type']
                                         == 'cash_receipt']['amount'].sum()
            match_amount = match_txn['matched_amount'].iloc[0]

            if abs(journal_amount - match_amount) > 1:
                error_msg = f"Amount mismatch for {txn_id}: Journal={journal_amount}, Bank={match_amount}"
                errors.append(error_msg)

            # マッチングスコアの整合性
            journal_score = journal_txn['match_score'].iloc[0]
            match_score = match_txn['match_score'].iloc[0]

            if abs(journal_score - match_score) > 0.001:  # 小数点3桁まで許容
                warning_msg = f"Score mismatch for {txn_id}: Journal={journal_score:.3f}, Match={match_score:.3f}"
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
        """金額整合性の検証"""
        if self.journal_df is None or self.match_df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        warnings = []

        # 同じ取引ID内での金額一貫性チェック
        for transaction_id in self.journal_df['transaction_id'].unique():
            txn_entries = self.journal_df[self.journal_df['transaction_id']
                                          == transaction_id]

            # 入金仕訳と売上仕訳の金額が一致するかチェック
            cash_amount = txn_entries[txn_entries['entry_type']
                                      == 'cash_receipt']['amount'].sum()
            revenue_amount = txn_entries[txn_entries['entry_type']
                                         == 'revenue_recognition']['amount'].sum()

            if abs(cash_amount - revenue_amount) > AMOUNT_TOLERANCE:
                warning_msg = f"Inconsistent amounts for {transaction_id}: Cash={cash_amount:,}, Revenue={revenue_amount:,}"
                warnings.append(warning_msg)

        # 異常値チェック（平均±3標準偏差の範囲外）
        mean_amount = self.journal_df['amount'].mean()
        std_amount = self.journal_df['amount'].std()

        outliers = self.journal_df[
            (self.journal_df['amount'] < mean_amount - OUTLIER_STDDEV * std_amount) |
            (self.journal_df['amount'] > mean_amount + OUTLIER_STDDEV * std_amount)
        ]

        if not outliers.empty:
            for _, row in outliers.iterrows():
                warning_msg = f"Outlier amount: {row['transaction_id']} = {row['amount']:,} yen"
                warnings.append(warning_msg)

        if not warnings:
            self.validation_results['amount_consistency'] = True
            logger.info("Amount consistency validation passed")
        else:
            self.validation_results['warnings'].extend(warnings)
            logger.warning(f"Amount consistency warnings: {warnings}")

        return True

    def validate_duplicate_entries(self) -> bool:
        """重複エントリの検証"""
        if self.journal_df is None:
            error_msg = "Journal DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        # 同じ取引ID・エントリタイプの重複チェック
        duplicate_entries = self.journal_df[self.journal_df.duplicated(
            subset=['transaction_id', 'entry_type'],
            keep=False
        )]

        if not duplicate_entries.empty:
            error_msg = f"Duplicate entries found: {len(duplicate_entries)} rows"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        # 同じ日付・取引ID・金額の重複チェック
        potential_duplicates = self.journal_df[self.journal_df.duplicated(
            subset=['date', 'transaction_id', 'amount'],
            keep=False
        )]

        if not potential_duplicates.empty:
            warning_msg = f"Potential duplicate entries found: {len(potential_duplicates)} rows"
            self.validation_results['warnings'].append(warning_msg)
            logger.warning(warning_msg)

        self.validation_results['duplicate_entries'] = True
        logger.info("Duplicate validation passed")
        return True

    def calculate_summary(self):
        """
        仕訳データのサマリー情報を計算し、件数やエントリタイプ別集計などをログ出力する。
        Returns:
            None
        """
        if self.journal_df is not None:
            self.validation_results['total_entries'] = len(self.journal_df)

            # エントリタイプ別集計
            entry_type_counts = self.journal_df['entry_type'].value_counts()

            logger.info(
                f"Summary: {self.validation_results['total_entries']} journal entries")
            logger.info(f"Entry types: {dict(entry_type_counts)}")
            logger.info(
                f"Total debit: {self.validation_results['total_debit']:,} yen")
            logger.info(
                f"Total credit: {self.validation_results['total_credit']:,} yen")

    def run_all_validations(self) -> Dict:
        """
        すべての検証（ファイル存在・読み込み・カラム・型・バランス・重複など）を実行し、
        検証結果dictを返す。
        Returns:
            dict: 検証結果
        """
        logger.info(f"Starting matching validation for: {self.journal_file}")

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
        self.validate_accounting_balance()
        self.validate_matching_consistency()
        self.validate_amount_consistency()
        self.validate_duplicate_entries()

        # サマリー計算
        self.calculate_summary()

        # 結果判定
        is_valid = (
            self.validation_results['file_exists'] and
            self.validation_results['file_readable'] and
            self.validation_results['required_columns'] and
            self.validation_results['data_types'] and
            self.validation_results['accounting_balance'] and
            self.validation_results['matching_consistency'] and
            self.validation_results['duplicate_entries']
        )

        if is_valid:
            logger.info("✅ Matching validation PASSED")
        else:
            logger.error("❌ Matching validation FAILED")

        return self.validation_results

    def generate_report(self) -> str:
        """検証レポートの生成"""
        report = []
        report.append("=" * 60)
        report.append("MATCHING VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Journal File: {self.journal_file}")
        report.append(f"Match Suggestion File: {self.match_suggestion_file}")
        report.append(
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # サマリー
        report.append("SUMMARY:")
        report.append(
            f"  Total Journal Entries: {self.validation_results['total_entries']}")
        report.append(
            f"  Total Debit Amount: {self.validation_results['total_debit']:,} yen")
        report.append(
            f"  Total Credit Amount: {self.validation_results['total_credit']:,} yen")
        report.append("")

        # 検証結果
        report.append("VALIDATION RESULTS:")
        for key, value in self.validation_results.items():
            if key in [
                'errors',
                'warnings',
                'total_entries',
                'total_debit',
                    'total_credit']:
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
    # 最新の仕訳ファイルを検索
    journal_dir = "output/journal"
    if not os.path.exists(journal_dir):
        logger.error(f"Journal directory not found: {journal_dir}")
        return

    journal_files = [f for f in os.listdir(
        journal_dir) if f.startswith('journal_') and f.endswith('.csv')]

    if not journal_files:
        logger.error("No journal files found")
        return

    # 最新のファイルを選択
    latest_journal = sorted(journal_files)[-1]
    journal_path = os.path.join(journal_dir, latest_journal)

    # 最新のマッチング提案ファイルを検索
    match_dir = "output/ai_output"
    if not os.path.exists(match_dir):
        logger.error(f"AI output directory not found: {match_dir}")
        return

    match_files = [f for f in os.listdir(match_dir) if f.startswith(
        'match_suggestion_') and f.endswith('.csv')]

    if not match_files:
        logger.error("No match suggestion files found")
        return

    # 最新のファイルを選択
    latest_match = sorted(match_files)[-1]
    match_path = os.path.join(match_dir, latest_match)

    # 検証実行
    validator = MatchingValidator(journal_path, match_path)
    results = validator.run_all_validations()

    # レポート生成・出力
    report = validator.generate_report()
    print(report)

    # レポートファイル保存
    report_dir = "output/reports"
    os.makedirs(report_dir, exist_ok=True)

    report_filename = f"matching_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = os.path.join(report_dir, report_filename)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"Validation report saved: {report_path}")

    # 検証結果に基づく終了コード
    if results['errors']:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    main()
