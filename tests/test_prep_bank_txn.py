import os
import pandas as pd
import pytest
from src.data_processing.prep_bank_txn import BankTransactionProcessor

def test_load_bank_data_normal():
    processor = BankTransactionProcessor("data/test/bank_test.csv")
    assert processor.load_bank_data() is True
    assert isinstance(processor.df, pd.DataFrame)
    assert len(processor.df) == 2

def test_load_bank_data_file_not_found():
    processor = BankTransactionProcessor("data/not_exist.csv")
    assert processor.load_bank_data() is False
    assert processor.df is None

def test_validate_data_structure():
    processor = BankTransactionProcessor("data/test/bank_test.csv")
    processor.load_bank_data()
    assert processor.validate_data_structure() is True

def test_clean_transaction_data():
    processor = BankTransactionProcessor("data/test/bank_test.csv")
    processor.load_bank_data()
    cleaned = processor.clean_transaction_data()
    assert isinstance(cleaned, pd.DataFrame)
    assert len(cleaned) == 2
    assert all(cleaned['Amount'] > 0)

def test_add_processing_metadata():
    processor = BankTransactionProcessor("data/test/bank_test.csv")
    processor.load_bank_data()
    cleaned = processor.clean_transaction_data()
    meta_df = processor.add_processing_metadata(cleaned)
    assert 'processed_at' in meta_df.columns
    assert 'transaction_id' in meta_df.columns
    assert 'year' in meta_df.columns
    assert 'month' in meta_df.columns
    assert 'amount_category' in meta_df.columns

def test_match_with_accounts_receivable():
    processor = BankTransactionProcessor("data/test/bank_test.csv")
    processor.load_bank_data()
    cleaned = processor.clean_transaction_data()
    meta_df = processor.add_processing_metadata(cleaned)
    # テスト用売掛金データが存在する場合
    ar_file = "data/Updated_Accounts_Receivable_test.csv"
    if os.path.exists(ar_file):
        matched = processor.match_with_accounts_receivable(meta_df)
        assert 'matching_status' in matched.columns
        assert 'matching_confidence' in matched.columns
    else:
        # ファイルがなければno_ar_dataで返る
        matched = processor.match_with_accounts_receivable(meta_df)
        assert (matched['matching_status'] == 'no_ar_data').all() 