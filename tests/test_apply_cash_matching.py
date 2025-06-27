import os
import pandas as pd
import pytest
from src.data_processing.apply_cash_matching import CashMatchingProcessor

def make_match_suggestion_df():
    return pd.DataFrame([
        {
            'transaction_id': 'TXN_20240601_0001',
            'project_id': 'PRJ_0001',
            'client_name': 'A社',
            'amount': 100000,
            'matched_amount': 100000,
            'match_score': 0.9
        },
        {
            'transaction_id': 'TXN_20240602_0002',
            'project_id': 'PRJ_0002',
            'client_name': 'B社',
            'amount': 200000,
            'matched_amount': 150000,
            'match_score': 0.6
        }
    ])

def make_bank_data_df():
    return pd.DataFrame([
        {
            'Transaction_Date': '2024-06-01',
            'Client_Name': 'A社',
            'Amount': 100000,
            'Transaction_Type': '入金',
            'transaction_id': 'TXN_20240601_0001'
        },
        {
            'Transaction_Date': '2024-06-02',
            'Client_Name': 'B社',
            'Amount': 200000,
            'Transaction_Type': '入金',
            'transaction_id': 'TXN_20240602_0002'
        }
    ])

def make_invoice_seed_df():
    return pd.DataFrame([
        {
            'project_id': 'PRJ_0001',
            'client_id': 'Client_004',
            'client_name': 'A社',
            'project_name': 'プロジェクトA',
            'pm_id': 'ishida.kento',
            'billing_year': 2024,
            'billing_month': 6,
            'billing_amount': 100000
        },
        {
            'project_id': 'PRJ_0002',
            'client_id': 'Client_001',
            'client_name': 'B社',
            'project_name': 'プロジェクトB',
            'pm_id': 'takahashi.misaki',
            'billing_year': 2024,
            'billing_month': 6,
            'billing_amount': 200000
        }
    ])

def test_load_data(tmp_path):
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    make_match_suggestion_df().to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    assert processor.load_data() is True
    assert processor.match_df is not None
    assert processor.bank_df is not None
    assert processor.invoice_df is not None

def test_validate_match_suggestions(tmp_path):
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    make_match_suggestion_df().to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    processor.load_data()
    assert processor.validate_match_suggestions() is True

def test_filter_high_confidence_matches(tmp_path):
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    make_match_suggestion_df().to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    processor.load_data()
    high_conf = processor.filter_high_confidence_matches(0.7)
    assert len(high_conf) == 1
    assert high_conf.iloc[0]['match_score'] >= 0.7

def test_create_journal_entries(tmp_path):
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    make_match_suggestion_df().to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    processor.load_data()
    high_conf = processor.filter_high_confidence_matches(0.7)
    journal_df = processor.create_journal_entries(high_conf)
    assert len(journal_df) == 2  # 2 entries per high confidence match
    assert 'debit_account' in journal_df.columns
    assert 'credit_account' in journal_df.columns

def test_add_manual_review_entries(tmp_path):
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    make_match_suggestion_df().to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    processor.load_data()
    low_conf = processor.match_df[processor.match_df['match_score'] < 0.7]
    processor.journal_df = pd.DataFrame()  # Ensure it's empty
    journal_df = processor.add_manual_review_entries(low_conf)
    assert 'manual_review' in journal_df['entry_type'].values

def test_calculate_journal_statistics(tmp_path):
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    make_match_suggestion_df().to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    processor.load_data()
    high_conf = processor.filter_high_confidence_matches(0.7)
    processor.create_journal_entries(high_conf)
    stats = processor.calculate_journal_statistics()
    assert 'total_entries' in stats
    assert stats['total_entries'] > 0

def test_process(tmp_path):
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    make_match_suggestion_df().to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    journal_df, output_path = processor.process(confidence_threshold=0.7, output_dir=str(tmp_path))
    assert os.path.exists(output_path)
    assert len(journal_df) > 0

def test_validate_match_suggestions_invalid(tmp_path):
    # Missing required column
    match_df = make_match_suggestion_df().drop(columns=['amount'])
    match_path = tmp_path / "match.csv"
    bank_path = tmp_path / "bank.csv"
    invoice_path = tmp_path / "invoice.csv"
    match_df.to_csv(match_path, index=False)
    make_bank_data_df().to_csv(bank_path, index=False)
    make_invoice_seed_df().to_csv(invoice_path, index=False)
    processor = CashMatchingProcessor(str(match_path), str(bank_path), str(invoice_path))
    processor.load_data()
    assert processor.validate_match_suggestions() is False 