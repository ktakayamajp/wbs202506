import os
import base64
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config.settings import settings
from utils.logger import logger
from .email_recipient_manager import EmailRecipient, EmailRecipientManager


@dataclass
class InvoiceEmailData:
    """請求書メールデータクラス"""
    invoice_id: str
    project_id: str
    client_name: str
    project_name: str
    billing_amount: int
    billing_period: str
    due_date: str
    pdf_path: str
    recipient: EmailRecipient
    cc_recipients: List[EmailRecipient] = field(default_factory=list)
    bcc_recipients: List[EmailRecipient] = field(default_factory=list)
    custom_message: str = ""


class GmailEmailSender:
    """Gmail APIを使用したメール送信クラス"""

    # Gmail APIのスコープ
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']

    def __init__(self):
        self.service = None
        self.credentials = None
        self.sender_email = settings.GMAIL_SENDER
        self.recipient_manager = EmailRecipientManager()

        # 送信統計
        self.email_stats = {
            'total_sent': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'total_recipients': 0,
            'total_attachments': 0
        }

    def authenticate(self) -> bool:
        """Gmail API認証"""
        try:
            # 既存のトークンファイルをチェック
            token_path = 'data/gmail_token.json'
            creds = None

            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(
                    token_path, self.SCOPES)

            # トークンが無効または期限切れの場合
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # 新しい認証フロー
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'data/gmail_credentials.json', self.SCOPES)
                    creds = flow.run_local_server(port=0)

                # トークンを保存
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self.credentials = creds
            self.service = build('gmail', 'v1', credentials=creds)

            logger.info("Gmail API authentication successful")
            return True

        except Exception as e:
            logger.error(f"Gmail API authentication failed: {e}")
            return False

    def create_invoice_email(
            self,
            email_data: InvoiceEmailData) -> MIMEMultipart:
        """請求書メールの作成"""
        try:
            # メールの基本設定
            message = MIMEMultipart()
            message['to'] = email_data.recipient.email
            message['from'] = self.sender_email
            message['subject'] = f"請求書 - {email_data.project_name} ({email_data.invoice_id})"

            # CC、BCCの設定
            if email_data.cc_recipients:
                cc_emails = [r.email for r in email_data.cc_recipients]
                message['cc'] = ', '.join(cc_emails)

            if email_data.bcc_recipients:
                bcc_emails = [r.email for r in email_data.bcc_recipients]
                message['bcc'] = ', '.join(bcc_emails)

            # メール本文の作成
            body = self._create_email_body(email_data)
            message.attach(MIMEText(body, 'html', 'utf-8'))

            # PDF添付ファイルの追加
            if os.path.exists(email_data.pdf_path):
                self._attach_pdf(
                    message,
                    email_data.pdf_path,
                    email_data.invoice_id)
                self.email_stats['total_attachments'] += 1
            else:
                logger.warning(f"PDF file not found: {email_data.pdf_path}")

            return message

        except Exception as e:
            logger.error(f"Failed to create invoice email: {e}")
            raise

    def _create_email_body(self, email_data: InvoiceEmailData) -> str:
        """メール本文の作成"""
        # HTMLテンプレート
        html_template = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Hiragino Sans', 'Yu Gothic', sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f8f9fa; }
                .invoice-details { background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #2c3e50; }
                .amount { font-size: 18px; font-weight: bold; color: #e74c3c; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                .button { display: inline-block; padding: 10px 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>請求書送付のお知らせ</h1>
                </div>

                <div class="content">
                    <p>{{ recipient_name }} 様</p>

                    <p>平素より格別のご高配を賜り、厚く御礼申し上げます。</p>

                    <p>{{ billing_period }}分の請求書を添付いたします。</p>

                    <div class="invoice-details">
                        <h3>請求書詳細</h3>
                        <p><strong>プロジェクト名:</strong> {{ project_name }}</p>
                        <p><strong>請求期間:</strong> {{ billing_period }}</p>
                        <p><strong>請求金額:</strong> <span class="amount">¥{{ billing_amount }}</span></p>
                        <p><strong>お支払期限:</strong> {{ due_date }}</p>
                    </div>

                    {% if custom_message %}
                    <div class="invoice-details">
                        <h3>備考</h3>
                        <p>{{ custom_message }}</p>
                    </div>
                    {% endif %}

                    <p>ご不明な点がございましたら、お気軽にお問い合わせください。</p>

                    <p>今後ともよろしくお願いいたします。</p>

                    <p>敬具</p>
                </div>

                <div class="footer">
                    <p>株式会社サンプル<br>
                    東京都渋谷区○○○ 1-2-3<br>
                    TEL: 03-1234-5678 | Email: info@sample.co.jp</p>
                </div>
            </div>
        </body>
        </html>
        """

        # テンプレート変数の置換
        body = html_template.replace(
            '{{ recipient_name }}',
            email_data.recipient.name)
        body = body.replace('{{ project_name }}', email_data.project_name)
        body = body.replace('{{ billing_period }}', email_data.billing_period)
        
        # billing_amountを数値に変換してからフォーマット
        try:
            billing_amount_int = int(email_data.billing_amount)
            formatted_amount = f"{billing_amount_int:,}"
        except (ValueError, TypeError):
            formatted_amount = str(email_data.billing_amount)
        
        body = body.replace('{{ billing_amount }}', formatted_amount)
        body = body.replace('{{ due_date }}', email_data.due_date)
        body = body.replace('{{ custom_message }}', email_data.custom_message)

        return body

    def _attach_pdf(
            self,
            message: MIMEMultipart,
            pdf_path: str,
            invoice_id: str):
        """PDFファイルの添付"""
        try:
            with open(pdf_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= invoice_{invoice_id}.pdf'
            )

            message.attach(part)

        except Exception as e:
            logger.error(f"Failed to attach PDF: {e}")
            raise

    def send_email(self, message: MIMEMultipart) -> bool:
        """メール送信処理"""
        try:
            if self.service is None:
                logger.error("Gmail service is not authenticated.")
                return False
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {'raw': raw_message}
            self.service.users().messages().send(userId="me", body=send_message).execute()
            return True
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return False

    def prepare_email_data(
            self,
            invoice_id,
            project_id,
            client_name,
            project_name,
            billing_amount,
            billing_period,
            due_date,
            pdf_path,
            custom_message=""):
        """EmailRecipientManagerから送信先情報をセットしたInvoiceEmailDataを生成"""
        recipients = self.recipient_manager.get_recipients(project_id)
        if not recipients:
            raise ValueError(f"No recipient found for project_id={project_id}")
        cc_list = self.recipient_manager.get_cc_recipients()
        bcc_list = self.recipient_manager.get_bcc_recipients()
        return InvoiceEmailData(
            invoice_id=invoice_id,
            project_id=project_id,
            client_name=client_name,
            project_name=project_name,
            billing_amount=billing_amount,
            billing_period=billing_period,
            due_date=due_date,
            pdf_path=pdf_path,
            recipient=recipients[0],
            cc_recipients=cc_list,
            bcc_recipients=bcc_list,
            custom_message=custom_message
        )

    def send_invoice_email(self, email_data: InvoiceEmailData) -> bool:
        """請求書メールの送信"""
        try:
            print(f"[DEBUG] Creating email for {email_data.invoice_id}")
            # メールの作成
            message = self.create_invoice_email(email_data)

            print(f"[DEBUG] Sending email for {email_data.invoice_id}")
            # 送信
            success = self.send_email(message)

            if success:
                self.email_stats['total_sent'] += 1
                self.email_stats['total_recipients'] += 1

                # CC、BCC受信者のカウント
                if email_data.cc_recipients:
                    self.email_stats['total_recipients'] += len(
                        email_data.cc_recipients)
                if email_data.bcc_recipients:
                    self.email_stats['total_recipients'] += len(
                        email_data.bcc_recipients)

                logger.info(
                    f"Invoice email sent to {email_data.recipient.email}")
                print(f"[DEBUG] Email sent successfully to {email_data.recipient.email}")

            else:
                print(f"[DEBUG] Email send returned False for {email_data.invoice_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            print(f"[DEBUG] Exception in send_invoice_email: {e}")
            return False

    def send_batch_invoice_emails(
            self, email_data_list: List[InvoiceEmailData]) -> Dict[str, Any]:
        """複数の請求書メールを一括送信"""
        logger.info(
            f"Starting batch email sending: {len(email_data_list)} emails")

        results = {
            'total_emails': len(email_data_list),
            'successful_sends': 0,
            'failed_sends': 0,
            'failed_invoices': []
        }

        for email_data in email_data_list:
            try:
                print(f"[DEBUG] Sending email for {email_data.invoice_id} to {email_data.recipient.email}")
                success = self.send_invoice_email(email_data)

                if success:
                    results['successful_sends'] += 1
                    print(f"[DEBUG] Email sent successfully for {email_data.invoice_id}")
                else:
                    results['failed_sends'] += 1
                    results['failed_invoices'].append(email_data.invoice_id)
                    print(f"[DEBUG] Email failed for {email_data.invoice_id}")

            except Exception as e:
                logger.error(
                    f"Failed to send email for {email_data.invoice_id}: {e}")
                print(f"[DEBUG] Exception sending email for {email_data.invoice_id}: {e}")
                results['failed_sends'] += 1
                results['failed_invoices'].append(email_data.invoice_id)

        logger.info(f"Batch email sending completed: {results['successful_sends']}/{results['total_emails']} successful")
        return results

    def get_email_statistics(self) -> Dict[str, Any]:
        """メール送信統計情報を取得"""
        return {
            'total_sent': self.email_stats['total_sent'],
            'successful_sends': self.email_stats['successful_sends'],
            'failed_sends': self.email_stats['failed_sends'],
            'success_rate': (
                self.email_stats['successful_sends'] /
                self.email_stats['total_sent'] *
                100) if self.email_stats['total_sent'] > 0 else 0,
            'total_recipients': self.email_stats['total_recipients'],
            'total_attachments': self.email_stats['total_attachments']}


def main():
    """実際の請求書メール送信処理"""
    import glob
    import json
    from pathlib import Path

    # 最新の請求書ドラフトファイルを検索（テストファイルを除外）
    draft_files = glob.glob("output/ai_output/draft_invoice_*.json")
    if not draft_files:
        logger.error("No draft invoice files found")
        print("[ERROR] No draft invoice files found")
        return

    # テストファイルを除外して最新のファイルを選択
    non_test_files = [f for f in draft_files if "test" not in f.lower()]
    if not non_test_files:
        logger.error("No non-test draft invoice files found")
        print("[ERROR] No non-test draft invoice files found")
        return

    latest_draft = sorted(non_test_files)[-1]
    print(f"[DEBUG] Selected draft file: {latest_draft}")

    # 最新のPDFファイルを検索
    pdf_files = glob.glob("output/invoices/invoice_*.pdf")
    if not pdf_files:
        logger.error("No invoice PDF files found")
        print("[ERROR] No invoice PDF files found")
        return

    print(f"[DEBUG] Found {len(pdf_files)} PDF files in total")
    print(f"[DEBUG] PDF files: {pdf_files[:5]}...")  # 最初の5件を表示

    # ドラフトデータの読み込み
    with open(latest_draft, 'r', encoding='utf-8') as f:
        draft_data = json.load(f)

    print(f"[DEBUG] Loaded {len(draft_data)} projects from draft file")
    print(f"[DEBUG] Project IDs: {[d.get('project_id', 'UNKNOWN') for d in draft_data]}")

    # メール送信器の初期化
    sender = GmailEmailSender()

    try:
        # 認証
        auth_success = sender.authenticate()

        if not auth_success:
            print("[ERROR] Gmail API authentication failed")
            return

        print("[OK] Gmail API authentication successful")

        # 各請求書に対してメール送信
        email_data_list = []

        for draft in draft_data:
            project_id = draft.get('project_id', 'UNKNOWN')
            client_name = draft.get('client_name', 'Unknown Client')
            project_name = draft.get('project_name', 'Unknown Project')
            billing_amount = draft.get('billing_amount', 0)

            print(f"[DEBUG] Processing project: {project_id}")

            # 対応するPDFファイルを検索（最新のファイルを選択、テストファイルを除外）
            pdf_file = None
            matching_pdfs = []
            for pdf_path in pdf_files:
                if project_id in pdf_path and "test" not in pdf_path.lower():
                    matching_pdfs.append(pdf_path)
            
            if matching_pdfs:
                # 最新のファイルを選択（ファイル名のタイムスタンプでソート）
                pdf_file = sorted(matching_pdfs)[-1]
                print(f"[DEBUG] Found PDF file: {pdf_file}")
            else:
                logger.warning(f"PDF file not found for project {project_id}")
                print(f"[DEBUG] PDF file not found for project {project_id}")
                continue

            try:
                # メールデータの作成
                email_data = sender.prepare_email_data(
                    invoice_id=f"INV-{project_id}",
                    project_id=project_id,
                    client_name=client_name,
                    project_name=project_name,
                    billing_amount=billing_amount,
                    billing_period="2025年6月分",
                    due_date="2025年7月22日",
                    pdf_path=pdf_file,
                    custom_message=""
                )

                email_data_list.append(email_data)
                print(f"[DEBUG] Email data prepared for project: {project_id}")

            except Exception as e:
                logger.error(f"Failed to prepare email data for {project_id}: {e}")
                print(f"[DEBUG] Failed to prepare email data for {project_id}: {e}")
                continue

        # バッチ送信実行
        if email_data_list:
            results = sender.send_batch_invoice_emails(email_data_list)

            print(f"[OK] Invoice email sent successfully")
            print(f"[INFO] Email stats: {results}")
        else:
            print("[WARNING] No email data prepared")

    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        print(f"[ERROR] Email sending failed: {e}")


if __name__ == "__main__":
    main()
