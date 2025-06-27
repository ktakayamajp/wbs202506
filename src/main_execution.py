#!/usr/bin/env python3
"""
メイン実行スクリプト - 月次請求・入金処理自動化システム

月次請求・入金処理自動化システムの統合実行スクリプト。
請求書生成・入金マッチングなどのワークフローをコマンドラインから一括実行できる。
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import traceback

# プロジェクトルートをパスに追加（インポート前に実行）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.payment_matcher import PaymentMatcher
from src.ai.invoice_draft_generator import InvoiceDraftGenerator
from src.notifications.slack_notifier import SlackNotifier, SlackMessage
from src.email_utils.invoice_email_sender import main as invoice_email_sender_main
from src.pdf_generation.build_invoice_pdf import main as build_invoice_pdf_main
from src.data_processing.prep_bank_txn import main as prep_bank_txn_main
from src.data_processing.make_invoice_seed import main as make_invoice_seed_main
from src.data_processing.convert_match_suggestion import MatchSuggestionConverter
from utils.logger import logger
from config.settings import settings


def run_invoice_generation():
    try:
        logger.info("=== 請求書生成処理 開始 ===")
        print("[1/3] 請求書シード生成...")
        make_invoice_seed_main()
        print("[2/3] AIによる請求書ドラフト生成...")
        # シードデータを読み込む
        seed_file = "output/seed/invoice_seed_202401.csv"
        if not os.path.exists(seed_file):
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
        import csv
        projects = []
        with open(seed_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                projects.append(row)
        
        # PM名のマッピング（pm_id → pm_name）
        pm_mapping = {
            'ishida.kento': '石田 健人',
            'takahashi.misaki': '高橋 美咲',
            'suzuki.akiko': '鈴木 亜希子',
            'yamamoto.saori': '山本 沙織',
            'ito.kenichi': '伊藤 健一',
            'ogawa.mai': '小川 舞',
            'sato.hiroshi': '佐藤 博',
            'matsumoto.megumi': '松本 恵',
            'yamazaki.masato': '山崎 正人'
        }
        
        ai = InvoiceDraftGenerator()
        drafts = []
        for i, project in enumerate(projects):
            print(
                f"  - [{i + 1}/{len(projects)}] {project.get('project_name')} のドラフト生成中...")
            
            # pm_idをpm_nameに変換
            pm_id = project.get('pm_id', 'Unknown')
            pm_name = pm_mapping.get(pm_id, pm_id)  # マッピングにない場合はpm_idをそのまま使用
            
            # AI処理用のデータを準備
            ai_project_data = {
                'client_name': project.get('client_name'),
                'project_name': project.get('project_name'),
                'billing_amount': int(project.get('billing_amount', 0)),
                'pm_name': pm_name
            }
            
            draft = ai.generate_draft(ai_project_data)
            draft.update(project)
            draft['pm_name'] = pm_name  # 元のデータも更新
            drafts.append(draft)
        # 保存
        output_path = "output/ai_output/draft_invoice_202401.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(drafts, f, ensure_ascii=False, indent=2)
        print(f"[3/3] PDF生成・メール送信...")
        build_invoice_pdf_main()
        invoice_email_sender_main()
        print("=== 請求書生成処理 完了 ===")
        SlackNotifier().send_message(
            SlackMessage(
                channel=settings.SLACK_DEFAULT_CHANNEL,
                text=f"請求書生成処理が正常に完了しました。生成数: {len(drafts)}"
            )
        )
    except Exception as e:
        error_msg = f"請求書生成処理でエラーが発生しました: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        SlackNotifier().send_message(
            SlackMessage(
                channel=settings.SLACK_DEFAULT_CHANNEL,
                text=error_msg
            )
        )
        raise


def run_payment_matching():
    try:
        logger.info("=== 入金マッチング処理 開始 ===")
        print("[1/3] 銀行データ前処理...")
        prep_bank_txn_main()
        print("[2/3] AIによる入金マッチング...")
        invoice_file = "output/ai_output/draft_invoice_202401.json"
        payment_file = "data/03_Bank_Data_Final.csv"
        if not os.path.exists(
                invoice_file) or not os.path.exists(payment_file):
            raise FileNotFoundError("請求書または入金データファイルが見つかりません")
        with open(invoice_file, encoding="utf-8") as f:
            invoices = json.load(f)
        import csv
        payments = []
        with open(payment_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                payments.append(row)
        ai = PaymentMatcher()
        print(f"  - 請求書{len(invoices)}件、入金{len(payments)}件をAIでマッチング中...")
        matches = ai.match(invoices, payments)
        output_path = "output/ai_output/match_suggestion_202401.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        print("[3/3] JSON→CSV変換処理...")
        # JSON→CSV変換処理を追加
        json_file = "output/ai_output/match_suggestion_202401.json"
        csv_file = "output/ai_output/match_suggestion_202401.csv"
        converter = MatchSuggestionConverter(json_file, csv_file, invoice_file)
        if converter.convert():
            logger.info("JSON→CSV変換処理が正常に完了しました")
            print(f"  - CSVファイル生成完了: {csv_file}")
        else:
            logger.error("JSON→CSV変換処理に失敗しました")
            print("  - CSVファイル生成に失敗しました")
        
        print("=== 入金マッチング処理 完了 ===")
        SlackNotifier().send_message(
            SlackMessage(
                channel=settings.SLACK_DEFAULT_CHANNEL,
                text=f"入金マッチング処理が正常に完了しました。マッチ数: {len(matches)}"
            )
        )
    except Exception as e:
        error_msg = f"入金マッチング処理でエラーが発生しました: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        SlackNotifier().send_message(
            SlackMessage(
                channel=settings.SLACK_DEFAULT_CHANNEL,
                text=error_msg
            )
        )
        raise


def main():
    """
    コマンドライン引数で指定されたモード（invoice/matching）に応じて
    請求書生成または入金マッチングのワークフローを実行する。
    """
    parser = argparse.ArgumentParser(description="月次請求・入金処理自動化 統合実行スクリプト")
    parser.add_argument(
        "--mode", choices=["invoice", "matching"], required=True,
        help="実行する処理種別: invoice=請求書生成, matching=入金マッチング"
    )
    args = parser.parse_args()

    if args.mode == "invoice":
        run_invoice_generation()
    elif args.mode == "matching":
        run_payment_matching()
    else:
        logger.error(f"不明なmode: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
