import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class EmailTemplate:
    """メールテンプレートデータクラス"""
    subject: str
    html_body: str
    text_body: str


class EmailTemplateManager:
    """メールテンプレート管理クラス"""

    def __init__(self):
        self.templates = {}
        self._load_templates()

    def _load_templates(self):
        """テンプレートの読み込み"""
        self.templates = {
            'invoice_notification': self._get_invoice_notification_template(),
            'approval_request': self._get_approval_request_template(),
            'approval_reminder': self._get_approval_reminder_template(),
            'payment_confirmation': self._get_payment_confirmation_template(),
            'system_notification': self._get_system_notification_template(),
            'error_notification': self._get_error_notification_template()
        }

    def get_template(self, template_name: str) -> Optional[EmailTemplate]:
        """テンプレートの取得"""
        return self.templates.get(template_name)

    def render_template(self,
                        template_name: str,
                        context: Dict[str,
                                      Any]) -> Optional[EmailTemplate]:
        """テンプレートのレンダリング"""
        template = self.get_template(template_name)
        if not template:
            return None

        # コンテキスト変数の置換
        rendered_template = EmailTemplate(
            subject=self._replace_variables(template.subject, context),
            html_body=self._replace_variables(template.html_body, context),
            text_body=self._replace_variables(template.text_body, context)
        )

        return rendered_template

    def _replace_variables(self, text: str, context: Dict[str, Any]) -> str:
        """変数の置換"""
        for key, value in context.items():
            placeholder = f"{{{{ {key} }}}}"
            text = text.replace(placeholder, str(value))
        return text

    def _get_invoice_notification_template(self) -> EmailTemplate:
        """請求書通知テンプレート"""
        subject = "請求書送付のお知らせ - {{ project_name }} ({{ billing_period }})"

        html_body = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>請求書送付のお知らせ</title>
            <style>
                body {
                    font-family: 'Hiragino Sans', 'Yu Gothic', 'Meiryo', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                }
                .header {
                    background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }
                .header h1 {
                    margin: 0;
                    font-size: 24px;
                    font-weight: 300;
                }
                .content {
                    padding: 30px 20px;
                    background-color: #f8f9fa;
                }
                .greeting {
                    font-size: 16px;
                    margin-bottom: 20px;
                }
                .invoice-details {
                    background-color: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    border-left: 4px solid #3498db;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .invoice-details h3 {
                    margin-top: 0;
                    color: #2c3e50;
                }
                .detail-row {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }
                .detail-row:last-child {
                    border-bottom: none;
                    font-weight: bold;
                    font-size: 16px;
                }
                .amount {
                    color: #e74c3c;
                    font-size: 18px;
                }
                .footer {
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                }
                .company-info {
                    margin-bottom: 10px;
                }
                .contact-info {
                    color: #bdc3c7;
                }
                @media print {
                    .container { max-width: none; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>請求書送付のお知らせ</h1>
                </div>

                <div class="content">
                    <div class="greeting">
                        <p>{{ recipient_name }} 様</p>
                        <p>平素より格別のご高配を賜り、厚く御礼申し上げます。</p>
                    </div>

                    <p>{{ billing_period }}分の請求書を添付いたします。</p>

                    <div class="invoice-details">
                        <h3>請求書詳細</h3>
                        <div class="detail-row">
                            <span>プロジェクト名:</span>
                            <span>{{ project_name }}</span>
                        </div>
                        <div class="detail-row">
                            <span>請求期間:</span>
                            <span>{{ billing_period }}</span>
                        </div>
                        <div class="detail-row">
                            <span>請求金額:</span>
                            <span class="amount">¥{{ billing_amount }}</span>
                        </div>
                        <div class="detail-row">
                            <span>お支払期限:</span>
                            <span>{{ due_date }}</span>
                        </div>
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
                    <div class="company-info">
                        <strong>株式会社サンプル</strong><br>
                        東京都渋谷区○○○ 1-2-3
                    </div>
                    <div class="contact-info">
                        TEL: 03-1234-5678 | FAX: 03-1234-5679<br>
                        Email: info@sample.co.jp
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = """
請求書送付のお知らせ

{{ recipient_name }} 様

平素より格別のご高配を賜り、厚く御礼申し上げます。

{{ billing_period }}分の請求書を添付いたします。

【請求書詳細】
プロジェクト名: {{ project_name }}
請求期間: {{ billing_period }}
請求金額: ¥{{ billing_amount }}
お支払期限: {{ due_date }}

{% if custom_message %}
【備考】
{{ custom_message }}
{% endif %}

ご不明な点がございましたら、お気軽にお問い合わせください。
今後ともよろしくお願いいたします。

敬具

---
株式会社サンプル
東京都渋谷区○○○ 1-2-3
TEL: 03-1234-5678 | FAX: 03-1234-5679
Email: info@sample.co.jp
        """

        return EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body)

    def _get_approval_request_template(self) -> EmailTemplate:
        """承認依頼テンプレート"""
        subject = "請求書承認依頼 - {{ project_name }}"

        html_body = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Hiragino Sans', sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #ff9900; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f8f9fa; }
                .approval-details { background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #ff9900; }
                .urgent { border-left-color: #e74c3c; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>請求書承認依頼</h1>
                </div>

                <div class="content">
                    <p>{{ approver_name }} 様</p>

                    <p>以下の請求書について承認をお願いいたします。</p>

                    <div class="approval-details {% if priority == 'urgent' %}urgent{% endif %}">
                        <h3>承認依頼詳細</h3>
                        <p><strong>プロジェクト名:</strong> {{ project_name }}</p>
                        <p><strong>クライアント:</strong> {{ client_name }}</p>
                        <p><strong>請求金額:</strong> ¥{{ billing_amount }}</p>
                        <p><strong>依頼者:</strong> {{ requestor }}</p>
                        <p><strong>承認期限:</strong> {{ due_date }}</p>
                        <p><strong>優先度:</strong> {{ priority }}</p>
                    </div>

                    <p>承認期限までにご確認をお願いいたします。</p>
                </div>

                <div class="footer">
                    <p>このメールは自動送信されています。</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = """
請求書承認依頼

{{ approver_name }} 様

以下の請求書について承認をお願いいたします。

【承認依頼詳細】
プロジェクト名: {{ project_name }}
クライアント: {{ client_name }}
請求金額: ¥{{ billing_amount }}
依頼者: {{ requestor }}
承認期限: {{ due_date }}
優先度: {{ priority }}

承認期限までにご確認をお願いいたします。

---
このメールは自動送信されています。
        """

        return EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body)

    def _get_approval_reminder_template(self) -> EmailTemplate:
        """承認リマインドテンプレート"""
        subject = "【リマインド】請求書承認依頼 - {{ project_name }}"

        html_body = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Hiragino Sans', sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #e74c3c; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f8f9fa; }
                .reminder-details { background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #e74c3c; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>承認期限リマインド</h1>
                </div>

                <div class="content">
                    <p>{{ approver_name }} 様</p>

                    <p>承認期限まであと{{ hours_remaining }}時間です。</p>

                    <div class="reminder-details">
                        <h3>承認依頼詳細</h3>
                        <p><strong>プロジェクト名:</strong> {{ project_name }}</p>
                        <p><strong>クライアント:</strong> {{ client_name }}</p>
                        <p><strong>請求金額:</strong> ¥{{ billing_amount }}</p>
                        <p><strong>承認期限:</strong> {{ due_date }}</p>
                    </div>

                    <p>至急ご確認をお願いいたします。</p>
                </div>

                <div class="footer">
                    <p>このメールは自動送信されています。</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = """
承認期限リマインド

{{ approver_name }} 様

承認期限まであと{{ hours_remaining }}時間です。

【承認依頼詳細】
プロジェクト名: {{ project_name }}
クライアント: {{ client_name }}
請求金額: ¥{{ billing_amount }}
承認期限: {{ due_date }}

至急ご確認をお願いいたします。

---
このメールは自動送信されています。
        """

        return EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body)

    def _get_payment_confirmation_template(self) -> EmailTemplate:
        """入金確認テンプレート"""
        subject = "入金確認のお知らせ - {{ project_name }}"

        html_body = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Hiragino Sans', sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f8f9fa; }
                .payment-details { background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #27ae60; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>入金確認のお知らせ</h1>
                </div>

                <div class="content">
                    <p>{{ client_name }} 様</p>

                    <p>以下の入金を確認いたしました。</p>

                    <div class="payment-details">
                        <h3>入金詳細</h3>
                        <p><strong>プロジェクト名:</strong> {{ project_name }}</p>
                        <p><strong>入金日:</strong> {{ payment_date }}</p>
                        <p><strong>入金金額:</strong> ¥{{ payment_amount }}</p>
                        <p><strong>入金方法:</strong> {{ payment_method }}</p>
                    </div>

                    <p>ありがとうございました。</p>
                </div>

                <div class="footer">
                    <p>このメールは自動送信されています。</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = """
入金確認のお知らせ

{{ client_name }} 様

以下の入金を確認いたしました。

【入金詳細】
プロジェクト名: {{ project_name }}
入金日: {{ payment_date }}
入金金額: ¥{{ payment_amount }}
入金方法: {{ payment_method }}

ありがとうございました。

---
このメールは自動送信されています。
        """

        return EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body)

    def _get_system_notification_template(self) -> EmailTemplate:
        """システム通知テンプレート"""
        subject = "システム通知 - {{ notification_type }}"

        html_body = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Hiragino Sans', sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #3498db; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f8f9fa; }
                .notification-details { background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>システム通知</h1>
                </div>

                <div class="content">
                    <div class="notification-details">
                        <h3>{{ notification_title }}</h3>
                        <p><strong>通知タイプ:</strong> {{ notification_type }}</p>
                        <p><strong>発生時刻:</strong> {{ timestamp }}</p>
                        <p><strong>詳細:</strong></p>
                        <p>{{ message }}</p>
                    </div>
                </div>

                <div class="footer">
                    <p>このメールは自動送信されています。</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = """
システム通知

【{{ notification_title }}】
通知タイプ: {{ notification_type }}
発生時刻: {{ timestamp }}

詳細:
{{ message }}

---
このメールは自動送信されています。
        """

        return EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body)

    def _get_error_notification_template(self) -> EmailTemplate:
        """エラー通知テンプレート"""
        subject = "【重要】システムエラー発生 - {{ error_type }}"

        html_body = """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: 'Hiragino Sans', sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #e74c3c; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background-color: #f8f9fa; }
                .error-details { background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #e74c3c; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>システムエラー発生</h1>
                </div>

                <div class="content">
                    <div class="error-details">
                        <h3>エラー詳細</h3>
                        <p><strong>エラータイプ:</strong> {{ error_type }}</p>
                        <p><strong>発生時刻:</strong> {{ timestamp }}</p>
                        <p><strong>エラーメッセージ:</strong></p>
                        <p>{{ error_message }}</p>
                        {% if stack_trace %}
                        <p><strong>スタックトレース:</strong></p>
                        <pre>{{ stack_trace }}</pre>
                        {% endif %}
                    </div>

                    <p>至急対応をお願いいたします。</p>
                </div>

                <div class="footer">
                    <p>このメールは自動送信されています。</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = """
システムエラー発生

【エラー詳細】
エラータイプ: {{ error_type }}
発生時刻: {{ timestamp }}

エラーメッセージ:
{{ error_message }}

{% if stack_trace %}
スタックトレース:
{{ stack_trace }}
{% endif %}

至急対応をお願いいたします。

---
このメールは自動送信されています。
        """

        return EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body)


def main():
    """テスト用メイン処理"""
    # テンプレート管理器の初期化
    template_manager = EmailTemplateManager()

    # テスト用のコンテキスト
    context = {
        'recipient_name': 'テスト太郎',
        'project_name': 'システム開発プロジェクトA',
        'billing_period': '2025年6月分',
        'billing_amount': '1,500,000',
        'due_date': '2025年7月22日',
        'custom_message': '追加機能の開発を含む'
    }

    try:
        # 請求書通知テンプレートのテスト
        template = template_manager.render_template(
            'invoice_notification', context)

        if template:
            print("✅ Email template rendered successfully")
            print(f"Subject: {template.subject}")
            print(f"HTML length: {len(template.html_body)} characters")
            print(f"Text length: {len(template.text_body)} characters")
        else:
            print("❌ Failed to render email template")

        # 利用可能なテンプレート一覧
        template_names = list(template_manager.templates.keys())
        print(f"📋 Available templates: {', '.join(template_names)}")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()
