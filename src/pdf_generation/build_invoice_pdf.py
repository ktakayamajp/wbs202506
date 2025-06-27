import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from config.settings import settings
from config.constants import DRAFT_INVOICE_PATTERN, DUE_DATE_OFFSET_DAYS
from utils.logger import logger


class InvoicePDFGenerator:
    """請求書PDF生成クラス"""

    def __init__(
            self,
            template_dir: str = "templates",
            static_dir: str = "static"):
        self.template_dir = template_dir
        self.static_dir = static_dir
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self.font_config = FontConfiguration()
        self.generation_stats = {
            'total_invoices': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'total_pages': 0
        }

    def load_draft_invoice_data(self, draft_file: str) -> List[Dict]:
        """AI生成の請求書ドラフトデータを読み込み"""
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                draft_data = json.load(f)

            logger.info(f"Loaded draft invoice data: {len(draft_data)} invoices")
            return draft_data

        except Exception as e:
            logger.error(f"Failed to load draft invoice data: {e}")
            raise

    def validate_draft_data(self, draft_data: List[Dict]) -> bool:
        """ドラフトデータの検証"""
        required_fields = [
            'project_id', 'client_name', 'project_name', 'billing_amount'
        ]

        for i, invoice in enumerate(draft_data):
            missing_fields = [
                field for field in required_fields if field not in invoice]
            if missing_fields:
                logger.error(
                    f"Invoice {i}: Missing required fields: {missing_fields}")
                return False

            # 金額の妥当性チェック（文字列も数値も対応）
            billing_amount = invoice.get('billing_amount')
            try:
                # 文字列の場合は数値に変換
                if isinstance(billing_amount, str):
                    billing_amount = float(billing_amount)
                elif not isinstance(billing_amount, (int, float)):
                    logger.error(f"Invoice {i}: Invalid billing amount type: {type(billing_amount)}")
                    return False

                if billing_amount <= 0:
                    logger.error(f"Invoice {i}: Invalid billing amount: {billing_amount}")
                    return False
            except (ValueError, TypeError):
                logger.error(f"Invoice {i}: Cannot convert billing amount to number: {invoice.get('billing_amount')}")
                return False

        logger.info("Draft data validation passed")
        return True

    def prepare_invoice_context(
            self,
            invoice_data: Dict,
            company_info: Dict) -> Dict:
        """請求書テンプレート用のコンテキストを準備"""
        # 請求書番号の生成
        invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{invoice_data['project_id']}"

        # 日付の設定
        issue_date = datetime.now().strftime('%Y年%m月%d日')
        due_date = (datetime.now() + timedelta(days=DUE_DATE_OFFSET_DAYS)).strftime('%Y年%m月%d日')

        # 請求期間の設定
        billing_period = f"{datetime.now().strftime('%Y年%m月')}分"

        # 作業内容の設定（AI出力から取得、なければデフォルト）
        work_description = invoice_data.get('work_description', 'システム開発・保守業務')

        # 備考の設定
        notes = invoice_data.get('notes', '')

        # PM名の設定
        pm_name = invoice_data.get('pm_name', '担当者')

        context = {
            'company_name': company_info.get('name', '株式会社サンプル'),
            'company_address': company_info.get('address', '東京都渋谷区○○○ 1-2-3'),
            'company_phone': company_info.get('phone', '03-1234-5678'),
            'company_fax': company_info.get('fax', '03-1234-5679'),
            'company_email': company_info.get('email', 'info@sample.co.jp'),
            'company_logo': company_info.get('logo', None),
            'bank_account_info': company_info.get('bank_account', '○○銀行 ○○支店 普通 1234567'),

            'invoice_data': {
                'invoice_number': invoice_number,
                'issue_date': issue_date,
                'due_date': due_date,
                'client_name': invoice_data['client_name'],
                'project_id': invoice_data['project_id'],
                'project_name': invoice_data['project_name'],
                'billing_period': billing_period,
                'billing_amount': invoice_data['billing_amount'],
                'work_description': work_description,
                'notes': notes,
                'pm_name': pm_name
            }
        }

        return context

    def generate_html_content(self, context: Dict) -> str:
        """HTMLコンテンツの生成"""
        try:
            template = self.jinja_env.get_template('invoice_template.html')
            html_content = template.render(**context)

            logger.info("HTML content generated successfully")
            return html_content

        except Exception as e:
            logger.error(f"Failed to generate HTML content: {e}")
            raise

    def generate_pdf_from_html(
            self,
            html_content: str,
            output_path: str) -> bool:
        """HTMLからPDFを生成"""
        try:
            # CSSファイルのパス
            css_path = os.path.join(
                self.static_dir, 'css', 'invoice_styles.css')

            # WeasyPrintでPDF生成
            if os.path.exists(css_path):
                css = CSS(filename=css_path, font_config=self.font_config)
                HTML(string=html_content).write_pdf(
                    output_path,
                    stylesheets=[css],
                    font_config=self.font_config
                )
            else:
                # CSSファイルがない場合はインラインスタイルのみ使用
                HTML(string=html_content).write_pdf(
                    output_path,
                    font_config=self.font_config
                )

            logger.info(f"PDF generated successfully: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            return False

    def generate_single_invoice(
            self,
            invoice_data: Dict,
            company_info: Dict,
            output_dir: str) -> Optional[str]:
        """単一請求書のPDF生成"""
        try:
            # コンテキストの準備
            context = self.prepare_invoice_context(invoice_data, company_info)

            # HTMLコンテンツの生成
            html_content = self.generate_html_content(context)

            # 出力ファイル名の生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"invoice_{invoice_data['project_id']}_{timestamp}.pdf"
            output_path = os.path.join(output_dir, filename)

            # PDF生成
            if self.generate_pdf_from_html(html_content, output_path):
                self.generation_stats['successful_generations'] += 1
                return output_path
            else:
                self.generation_stats['failed_generations'] += 1
                return None

        except Exception as e:
            logger.error(f"Failed to generate invoice for {invoice_data.get('project_id', 'unknown')}: {e}")
            self.generation_stats['failed_generations'] += 1
            return None

    def generate_all_invoices(
            self,
            draft_file: str,
            company_info: Dict,
            output_dir: str = "output/invoices") -> List[str]:
        """全請求書のPDF生成"""
        logger.info(f"Starting PDF generation for: {draft_file}")

        # 出力ディレクトリの作成
        os.makedirs(output_dir, exist_ok=True)

        # ドラフトデータの読み込み
        draft_data = self.load_draft_invoice_data(draft_file)

        # データの検証
        if not self.validate_draft_data(draft_data):
            raise Exception("Draft data validation failed")

        self.generation_stats['total_invoices'] = len(draft_data)
        generated_files = []

        # 各請求書のPDF生成
        for invoice_data in draft_data:
            try:
                output_path = self.generate_single_invoice(
                    invoice_data, company_info, output_dir)
                if output_path:
                    generated_files.append(output_path)
                    logger.info(f"Generated: {output_path}")
                else:
                    logger.error(f"Failed to generate PDF for {invoice_data.get('project_id', 'unknown')}")

            except Exception as e:
                logger.error(f"Error processing invoice {invoice_data.get('project_id', 'unknown')}: {e}")
                self.generation_stats['failed_generations'] += 1

        # 統計情報の更新
        self.generation_stats['total_pages'] = len(
            generated_files)  # 1請求書1ページと仮定

        logger.info(
            f"PDF generation completed: {len(generated_files)}/{len(draft_data)} successful")
        return generated_files

    def generate_processing_report(self, generated_files: List[str]) -> str:
        """処理レポートの生成"""
        report = []
        report.append("=" * 60)
        report.append("INVOICE PDF GENERATION REPORT")
        report.append("=" * 60)
        report.append(f"Processing Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"  Total Invoices: {self.generation_stats['total_invoices']}")
        report.append(f"  Successful Generations: {self.generation_stats['successful_generations']}")
        report.append(f"  Failed Generations: {self.generation_stats['failed_generations']}")
        report.append(f"  Total Pages: {self.generation_stats['total_pages']}")
        report.append("")

        # 生成されたファイル一覧
        if generated_files:
            report.append("GENERATED FILES:")
            for file_path in generated_files:
                file_size = os.path.getsize(
                    file_path) if os.path.exists(file_path) else 0
                report.append(
                    f"  {os.path.basename(file_path)} ({file_size:,} bytes)")
        else:
            report.append("GENERATED FILES: None")

        report.append("=" * 60)

        return "\n".join(report)


def main():
    """メイン処理"""
    # 会社情報の設定
    company_info = {
        'name': '株式会社サンプル',
        'address': '東京都渋谷区○○○ 1-2-3',
        'phone': '03-1234-5678',
        'fax': '03-1234-5679',
        'email': 'info@sample.co.jp',
        'logo': None,  # ロゴファイルのパスを指定
        'bank_account': '○○銀行 ○○支店 普通 1234567'
    }

    # 最新のドラフトファイルを検索（テストファイルを除外）
    import glob
    draft_files = glob.glob("output/ai_output/draft_invoice_*.json")
    
    # テストファイルを除外
    draft_files = [f for f in draft_files if "test" not in f.lower()]
    
    if not draft_files:
        logger.error("No draft invoice files found (excluding test files)")
        return

    # 最新のファイルを選択
    latest_draft = sorted(draft_files)[-1]
    logger.info(f"Selected draft file: {latest_draft}")

    # PDF生成器の初期化
    generator = InvoicePDFGenerator()

    try:
        # PDF生成実行
        generated_files = generator.generate_all_invoices(
            latest_draft, company_info)

        # レポート生成・保存
        report = generator.generate_processing_report(generated_files)
        print(report)

        # レポートファイル保存
        report_dir = "output/reports"
        os.makedirs(report_dir, exist_ok=True)

        report_filename = f"pdf_generation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = os.path.join(report_dir, report_filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Generation report saved: {report_path}")

        print(f"[OK] PDF generation completed")
        print(f"[INFO] Generated {len(generated_files)} PDF files")
        print(f"[INFO] Success rate: {generator.generation_stats['successful_generations']}/{generator.generation_stats['total_invoices']}")

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        print(f"[ERROR] PDF generation failed: {e}")


if __name__ == "__main__":
    main()
