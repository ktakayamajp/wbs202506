import os
import tempfile
import pandas as pd
import pytest
from src.data_processing.bank_data_validator import BankDataValidator
from config.constants import YEAR_MIN, YEAR_MAX, MONTH_MIN, MONTH_MAX, MATCH_SCORE_MIN, MATCH_SCORE_MAX

def make_valid_bank_df():
    return pd.DataFrame([
        {
            'Transaction_Date': '2024-06-01',
            'Client_Name': 'A社',
            'Amount': 100000,
            'Transaction_Type': '入金',
            'processed_at': '2024-06-01 12:00:00',
            'transaction_id': 'TXN_20240601_0001',
            'year': 2024,
            'month': 6,
            'amount_category': 'small',
            'matching_status': 'matched',
            'matching_confidence': 0.9
        },
        {
            'Transaction_Date': '2024-06-02',
            'Client_Name': 'B社',
            'Amount': 200000,
            'Transaction_Type': '入金',
            'processed_at': '2024-06-02 12:00:00',
            'transaction_id': 'TXN_20240602_0002',
            'year': 2024,
            'month': 6,
            'amount_category': 'medium',
            'matching_status': 'unmatched',
            'matching_confidence': 0.5
        }
    ])

def test_validate_file_exists_and_readable(tmp_path):
    df = make_valid_bank_df()
    file_path = tmp_path / "bank_test.csv"
    df.to_csv(file_path, index=False)
    validator = BankDataValidator(str(file_path))
    assert validator.validate_file_exists() is True
    assert validator.validate_file_readable() is True
    assert validator.df is not None

def test_validate_required_columns(tmp_path):
    df = make_valid_bank_df()
    file_path = tmp_path / "bank_test.csv"
    df.to_csv(file_path, index=False)
    validator = BankDataValidator(str(file_path))
    validator.validate_file_readable()
    assert validator.validate_required_columns() is True

def test_validate_data_types(tmp_path):
    df = make_valid_bank_df()
    file_path = tmp_path / "bank_test.csv"
    df.to_csv(file_path, index=False)
    validator = BankDataValidator(str(file_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    assert validator.validate_data_types() is True

def test_validate_duplicates(tmp_path):
    df = make_valid_bank_df()
    # Add a duplicate row for transaction_id
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    file_path = tmp_path / "bank_test.csv"
    df.to_csv(file_path, index=False)
    validator = BankDataValidator(str(file_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    validator.validate_data_types()
    # Should fail due to duplicate transaction_id
    assert validator.validate_duplicates() is False
    assert any("Duplicate transaction_ids" in e for e in validator.validation_results['errors'])

def test_run_all_validations_valid(tmp_path):
    df = make_valid_bank_df()
    file_path = tmp_path / "bank_test.csv"
    df.to_csv(file_path, index=False)
    validator = BankDataValidator(str(file_path))
    results = validator.run_all_validations()
    assert results['file_exists'] is True
    assert results['file_readable'] is True
    assert results['required_columns'] is True
    assert results['data_types'] is True
    assert results['duplicates'] is True
    assert results['matching_consistency'] is True
    assert results['errors'] == []
    assert isinstance(validator.generate_report(), str)

def test_run_all_validations_invalid(tmp_path):
    # Missing required column
    df = make_valid_bank_df().drop(columns=['Amount'])
    file_path = tmp_path / "bank_test.csv"
    df.to_csv(file_path, index=False)
    validator = BankDataValidator(str(file_path))
    results = validator.run_all_validations()
    assert results['required_columns'] is False
    assert any("Missing required columns" in e for e in results['errors']) 