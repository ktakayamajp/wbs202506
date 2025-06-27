import pandas as pd
import re
from datetime import datetime
import os
from config.settings import settings
from config.constants import INVOICE_SEED_PATTERN, YEARMONTH_FORMAT
from utils.logger import logger
from typing import Dict


def log_data_comparison(before_data, after_data, stage_name):
    """データの差分比較ログを出力"""
    logger.info(f"=== {stage_name} 差分比較 ===")

    if isinstance(before_data, list) and isinstance(after_data, list):
        logger.info(f"処理前: {len(before_data)} 件")
        logger.info(f"処理後: {len(after_data)} 件")

        if before_data and after_data:
            # 最初の項目の差分を比較
            before_keys = set(before_data[0].keys())
            after_keys = set(after_data[0].keys())

            added_keys = after_keys - before_keys
            if added_keys:
                logger.info(f"追加されたフィールド: {list(added_keys)}")

            # 金額の合計比較
            before_total = sum(item.get('billing_amount', 0)
                               for item in before_data)
            after_total = sum(item.get('billing_amount', 0)
                              for item in after_data)
            logger.info(
                f"請求金額合計 - 処理前: {before_total:,} 円, 処理後: {after_total:,} 円")

            # サンプルデータの比較
            logger.info("処理前サンプル:")
            for i, item in enumerate(before_data[:3]):
                logger.info(f"  {i + 1}. {item}")

            logger.info("処理後サンプル:")
            for i, item in enumerate(after_data[:3]):
                logger.info(f"  {i + 1}. {item}")

    elif isinstance(before_data, pd.DataFrame) and isinstance(after_data, pd.DataFrame):
        logger.info(
            f"処理前: {len(before_data)} 行 x {len(before_data.columns)} 列")
        logger.info(f"処理後: {len(after_data)} 行 x {len(after_data.columns)} 列")

        # 列の差分
        before_cols = set(before_data.columns)
        after_cols = set(after_data.columns)
        added_cols = after_cols - before_cols
        if added_cols:
            logger.info(f"追加された列: {list(added_cols)}")

        # 金額列がある場合の合計比較
        if 'billing_amount' in before_data.columns and 'billing_amount' in after_data.columns:
            before_total = before_data['billing_amount'].sum()
            after_total = after_data['billing_amount'].sum()
            logger.info(
                f"請求金額合計 - 処理前: {before_total:,} 円, 処理後: {after_total:,} 円")

    logger.info(f"=== {stage_name} 差分比較完了 ===\n")


def parse_billing_contracts(file_path):
    """請求契約テキストファイルを解析してプロジェクト情報を抽出"""
    projects = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 処理前のログ
        logger.info(f"請求契約ファイル読み込み: {file_path}")
        logger.info(f"ファイル内容行数: {len(content.splitlines())}")

        # プロジェクト情報を正規表現で抽出
        pattern = r'PRJ_(\d+)、(.+?)\n(\d{4})年(\d{1,2})月度：\s*(\d+)\s*円'
        matches = re.findall(pattern, content)

        for match in matches:
            project_id = f"PRJ_{match[0].zfill(4)}"
            client_name = match[1].strip()
            year = match[2]
            month = match[3].zfill(2)
            amount = int(match[4])

            projects.append({
                'project_id': project_id,
                'client_name': client_name,
                'billing_year': year,
                'billing_month': month,
                'billing_amount': amount
            })

        logger.info(f"Parsed {len(projects)} projects from billing contracts")
        return projects

    except Exception as e:
        logger.error(f"Error parsing billing contracts: {e}")
        return []


def enrich_project_data(projects, project_master_path):
    """プロジェクトマスタから追加情報を取得"""
    try:
        # 処理前のデータを記録
        before_enrichment = projects.copy()

        project_df = pd.read_csv(project_master_path)
        logger.info(f"プロジェクトマスタ読み込み: {len(project_df)} 件")

        for project in projects:
            # プロジェクトマスタから情報を取得
            project_info = project_df[project_df['プロジェクトID']
                                      == project['project_id']]

            if not project_info.empty:
                project['client_id'] = project_info.iloc[0]['Client ID']
                project['project_name'] = project_info.iloc[0]['プロジェクト名称']
                project['pm_id'] = project_info.iloc[0]['プロジェクトマネージャID']
            else:
                project['client_id'] = 'Unknown'
                project['project_name'] = 'Unknown Project'
                project['pm_id'] = 'Unknown'

        # 差分比較ログ
        log_data_comparison(before_enrichment, projects, "プロジェクト情報補完")

        logger.info(f"Enriched data for {len(projects)} projects")
        return projects

    except Exception as e:
        logger.error(f"Error enriching project data: {e}")
        return projects


def generate_invoice_seed(projects, output_dir, yearmonth=None):
    """請求書シードCSVを生成"""
    if not projects:
        logger.error("No projects to process")
        return None

    # 年月の決定
    if yearmonth is None:
        # 最初のプロジェクトの年月を使用
        first_project = projects[0]
        year = first_project['billing_year']
        month = first_project['billing_month']
        yearmonth = f"{year}{month}"

    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)

    # ファイル名の生成
    filename = INVOICE_SEED_PATTERN.format(yearmonth=yearmonth)
    output_path = os.path.join(output_dir, filename)

    # DataFrameの作成
    df = pd.DataFrame(projects)

    # 列の順序を整理
    columns = [
        'project_id', 'client_id', 'client_name', 'project_name',
        'pm_id', 'billing_year', 'billing_month', 'billing_amount'
    ]
    df = df[columns]

    # CSVとして保存
    df.to_csv(output_path, index=False, encoding='utf-8')

    logger.info(f"Generated invoice seed: {output_path}")
    logger.info(f"Total projects: {len(df)}")
    logger.info(f"Total billing amount: {df['billing_amount'].sum():,} yen")

    return output_path


def main():
    """メイン処理"""
    logger.info("Starting invoice seed generation")

    # 入力ファイルパス
    billing_contracts_path = "data/01_Project_Billing_Contracts_Varied.txt"
    project_master_path = "data/Project_master.csv"

    # 出力ディレクトリ
    output_dir = "output/seed"

    # 請求契約の解析
    logger.info("=== 請求契約解析開始 ===")
    projects = parse_billing_contracts(billing_contracts_path)

    if not projects:
        logger.error("Failed to parse billing contracts")
        return

    # 解析結果の差分比較ログ
    log_data_comparison([], projects, "請求契約解析")

    # プロジェクト情報の補完
    logger.info("=== プロジェクト情報補完開始 ===")
    projects = enrich_project_data(projects, project_master_path)

    # 請求書シードの生成
    logger.info("=== 請求書シード生成開始 ===")
    output_path = generate_invoice_seed(projects, output_dir)

    if output_path:
        logger.info("Invoice seed generation completed successfully")
        print(f"Generated: {output_path}")

        # 最終結果の差分比較ログ
        final_df = pd.DataFrame(projects)
        log_data_comparison(pd.DataFrame(), final_df, "最終請求書シード")
    else:
        logger.error("Invoice seed generation failed")


if __name__ == "__main__":
    main()
