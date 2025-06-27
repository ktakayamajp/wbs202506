"""
pytest設定ファイル
すべてのテストファイルで共通の設定を行う
"""

import os
import sys
import shutil
import json

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def pytest_configure(config):
    """テスト実行前の設定"""
    # 必要なディレクトリを作成
    directories = [
        'output/ai_output',
        'output/invoices',
        'output/bank_processing',
        'output/reports',
        'output/seed',
        'data'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # テスト用ファイルをコピー
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    
    # email_recipients.jsonをコピー
    src_email_recipients = os.path.join(fixtures_dir, 'email_recipients.json')
    dst_email_recipients = os.path.join(project_root, 'data', 'email_recipients.json')
    if os.path.exists(src_email_recipients):
        shutil.copy2(src_email_recipients, dst_email_recipients)
    
    # draft_invoice_test.jsonをコピー
    src_draft_invoice = os.path.join(fixtures_dir, 'draft_invoice_test.json')
    dst_draft_invoice = os.path.join(project_root, 'output', 'ai_output', 'draft_invoice_test.json')
    if os.path.exists(src_draft_invoice):
        shutil.copy2(src_draft_invoice, dst_draft_invoice)
    
    # invoice_seed_202401.csvをコピー
    src_invoice_seed = os.path.join(fixtures_dir, 'invoice_seed_202401.csv')
    dst_invoice_seed = os.path.join(project_root, 'output', 'seed', 'invoice_seed_202401.csv')
    if os.path.exists(src_invoice_seed):
        shutil.copy2(src_invoice_seed, dst_invoice_seed)
    
    # ダミーのPDFファイルを作成（空ファイル）
    dummy_pdf = os.path.join(project_root, 'output', 'invoices', 'invoice_PRJ_0001_test.pdf')
    if not os.path.exists(dummy_pdf):
        with open(dummy_pdf, 'w') as f:
            f.write('Dummy PDF content for testing')
    
    # ダミーの銀行データファイルを作成
    dummy_bank_data = os.path.join(project_root, 'data', '03_Bank_Data_Final.csv')
    if not os.path.exists(dummy_bank_data):
        with open(dummy_bank_data, 'w', encoding='utf-8') as f:
            f.write('Transaction_Date,Amount,Client_Name,Description\n')
            f.write('2025-06-01,100000,テスト株式会社,テスト取引1\n')
            f.write('2025-06-02,200000,テスト株式会社2,テスト取引2\n')
    
    # ダミーの売掛金データファイルを作成
    dummy_ar_data = os.path.join(project_root, 'data', 'Updated_Accounts_Receivable.csv')
    if not os.path.exists(dummy_ar_data):
        with open(dummy_ar_data, 'w', encoding='utf-8') as f:
            f.write('Project_ID,Client,AR_Amount\n')
            f.write('PRJ_0001,テスト株式会社,100000\n')
            f.write('PRJ_0002,テスト株式会社2,200000\n') 