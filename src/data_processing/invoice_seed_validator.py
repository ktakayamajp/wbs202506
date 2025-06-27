"""
invoice_seed_validator.py

請求書シードデータ（CSV）の検証・バリデーションを行うモジュール。
必須カラム・データ型・範囲・重複・プロジェクトマスタとの整合性などをチェックし、
請求書発行やAI処理の前処理として利用。
"""
import pandas as pd
import os
from datetime import datetime
from typing import Dict
from config.settings import settings
from utils.logger import logger
from config.constants import YEAR_MIN, YEAR_MAX, MONTH_MIN, MONTH_MAX, OUTLIER_STDDEV, INVOICE_MONTHLY_LIMIT
from utils.data_utils import check_file_exists, read_csv_with_log, check_required_columns, find_duplicates


class InvoiceSeedValidator:
    """
    請求書シードCSVの検証・バリデーションを行うクラス。

    Attributes:
        file_path (str): 入力ファイルパス
        df (pd.DataFrame): シードデータ
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
            'project_master_consistency': False,
            'total_amount': 0,
            'total_projects': 0,
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
            'project_id', 'client_id', 'client_name', 'project_name',
            'pm_id', 'billing_year', 'billing_month', 'billing_amount'
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

        # project_id: 文字列でPRJ_で始まる
        if not self.df['project_id'].str.match(r'^PRJ_\d{4}$').all():
            errors.append("project_id format invalid (should be PRJ_XXXX)")

        # client_id: 文字列でClient_で始まる
        if not self.df['client_id'].str.match(r'^Client_\d+$').all():
            errors.append("client_id format invalid (should be Client_XXX)")

        # billing_year: 数値で2020-2030の範囲
        if not self.df['billing_year'].between(YEAR_MIN, YEAR_MAX).all():
            errors.append(f"billing_year out of valid range ({YEAR_MIN}-{YEAR_MAX})")

        # billing_month: 数値で1-12の範囲
        if not self.df['billing_month'].between(MONTH_MIN, MONTH_MAX).all():
            errors.append(f"billing_month out of valid range ({MONTH_MIN}-{MONTH_MAX})")

        # billing_amount: 正の数値
        if not (self.df['billing_amount'] > 0).all():
            errors.append("billing_amount must be positive")

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
        """データ範囲の検証"""
        if self.df is None:
            error_msg = "DataFrame is not loaded."
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False

        warnings = []

        # 請求金額の異常値チェック
        mean_amount = self.df['billing_amount'].mean()
        std_amount = self.df['billing_amount'].std()

        # 平均±3標準偏差の範囲外を警告
        outliers = self.df[
            (self.df['billing_amount'] < mean_amount - OUTLIER_STDDEV * std_amount) |
            (self.df['billing_amount'] > mean_amount + OUTLIER_STDDEV * std_amount)
        ]

        if not outliers.empty:
            for _, row in outliers.iterrows():
                warning_msg = f"Outlier billing amount: {row['billing_amount']:,} yen"
                warnings.append(warning_msg)

        # 月次請求の妥当性チェック（同じ月に複数の請求がある場合）
        monthly_counts = self.df.groupby(
            ['billing_year', 'billing_month']).size()
        if (monthly_counts > INVOICE_MONTHLY_LIMIT).any():
            warning_msg = "High number of invoices in a single month detected"
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
        # プロジェクトIDの重複チェック
        duplicate_projects = find_duplicates(self.df, ['project_id'])
        if not duplicate_projects.empty:
            error_msg = f"Duplicate project_ids found: {duplicate_projects['project_id'].tolist()}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        # 同じプロジェクトの同じ月の重複チェック
        duplicate_monthly = find_duplicates(self.df, ['project_id', 'billing_year', 'billing_month'])
        if not duplicate_monthly.empty:
            error_msg = f"Duplicate monthly billing found for projects: {duplicate_monthly['project_id'].tolist()}"
            self.validation_results['errors'].append(error_msg)
            logger.error(error_msg)
            return False
        self.validation_results['duplicates'] = True
        logger.info("Duplicate validation passed")
        return True

    def validate_project_master_consistency(self) -> bool:
        """プロジェクトマスタとの整合性確認"""
        if self.df is None:
            warning_msg = "DataFrame is not loaded, skipping consistency check"
            self.validation_results['warnings'].append(warning_msg)
            logger.warning(warning_msg)
            return True

        try:
            project_master_path = "data/Project_master.csv"
            if not os.path.exists(project_master_path):
                warning_msg = "Project master file not found, skipping consistency check"
                self.validation_results['warnings'].append(warning_msg)
                logger.warning(warning_msg)
                return True

            project_master = pd.read_csv(project_master_path)

            # シードファイルのプロジェクトIDがマスタに存在するかチェック
            missing_in_master = set(
                self.df['project_id']) - set(project_master['プロジェクトID'])

            if missing_in_master:
                warning_msg = f"Projects not found in master: {list(missing_in_master)}"
                self.validation_results['warnings'].append(warning_msg)
                logger.warning(warning_msg)

            self.validation_results['project_master_consistency'] = True
            logger.info("Project master consistency check completed")
            return True

        except Exception as e:
            warning_msg = f"Project master consistency check failed: {e}"
            self.validation_results['warnings'].append(warning_msg)
            logger.warning(warning_msg)
            return True

    def calculate_summary(self):
        """サマリー情報の計算"""
        if self.df is not None:
            self.validation_results['total_amount'] = self.df['billing_amount'].sum(
            )
            self.validation_results['total_projects'] = len(self.df)

            logger.info(
                f"Summary: {self.validation_results['total_projects']} projects, " f"Total amount: {self.validation_results['total_amount']:,} yen")

    def run_all_validations(self) -> Dict:
        """全検証を実行"""
        logger.info(f"Starting validation for: {self.file_path}")

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
        self.validate_project_master_consistency()

        # サマリー計算
        self.calculate_summary()

        # 結果判定
        is_valid = (
            self.validation_results['file_exists'] and
            self.validation_results['file_readable'] and
            self.validation_results['required_columns'] and
            self.validation_results['data_types'] and
            self.validation_results['duplicates']
        )

        if is_valid:
            logger.info("✅ Invoice seed validation PASSED")
        else:
            logger.error("❌ Invoice seed validation FAILED")

        return self.validation_results

    def generate_report(self) -> str:
        """検証レポートの生成"""
        report = []
        report.append("=" * 60)
        report.append("INVOICE SEED VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"File: {self.file_path}")
        report.append(
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # サマリー
        report.append("SUMMARY:")
        report.append(
            f"  Total Projects: {self.validation_results['total_projects']}")
        report.append(
            f"  Total Amount: {self.validation_results['total_amount']:,} yen")
        report.append("")

        # 検証結果
        report.append("VALIDATION RESULTS:")
        for key, value in self.validation_results.items():
            if key in ['errors', 'warnings', 'total_amount', 'total_projects']:
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
    # 最新のシードファイルを検索
    seed_dir = "output/seed"
    if not os.path.exists(seed_dir):
        logger.error(f"Seed directory not found: {seed_dir}")
        return

    seed_files = [f for f in os.listdir(seed_dir) if f.startswith(
        'invoice_seed_') and f.endswith('.csv')]

    if not seed_files:
        logger.error("No invoice seed files found")
        return

    # 最新のファイルを選択
    latest_file = sorted(seed_files)[-1]
    file_path = os.path.join(seed_dir, latest_file)

    # 検証実行
    validator = InvoiceSeedValidator(file_path)
    results = validator.run_all_validations()

    # レポート生成・出力
    report = validator.generate_report()
    print(report)

    # レポートファイル保存
    report_dir = "output/reports"
    os.makedirs(report_dir, exist_ok=True)

    report_filename = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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
