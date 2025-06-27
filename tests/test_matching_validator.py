import os
import pandas as pd
import pytest
from src.data_processing.matching_validator import MatchingValidator

def make_journal_df():
    now = pd.Timestamp('2024-06-01 12:00:00')
    return pd.DataFrame([
        {
            'date': now.date(),
            'transaction_id': 'TXN_20240601_0001',
            'project_id': 'PRJ_0001',
            'client_name': 'A社',
            'debit_account': '現金',
            'credit_account': '売掛金',
            'amount': 100000,
            'description': '入金消込',
            'match_score': 0.9,
            'entry_type': 'cash_receipt',
            'created_at': now
        },
        {
            'date': now.date(),
            'transaction_id': 'TXN_20240601_0001',
            'project_id': 'PRJ_0001',
            'client_name': 'A社',
            'debit_account': '売掛金',
            'credit_account': '売上',
            'amount': 100000,
            'description': '売上計上',
            'match_score': 0.9,
            'entry_type': 'revenue_recognition',
            'created_at': now
        }
    ])

def make_match_suggestion_df():
    return pd.DataFrame([
        {
            'transaction_id': 'TXN_20240601_0001',
            'project_id': 'PRJ_0001',
            'client_name': 'A社',
            'amount': 100000,
            'matched_amount': 100000,
            'match_score': 0.9
        }
    ])

def test_validate_file_exists_and_readable(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    make_journal_df().to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    assert validator.validate_file_exists() is True
    assert validator.validate_file_readable() is True
    assert validator.journal_df is not None
    assert validator.match_df is not None

def test_validate_required_columns(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    make_journal_df().to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    validator.validate_file_readable()
    assert validator.validate_required_columns() is True

def test_validate_data_types(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    make_journal_df().to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    assert validator.validate_data_types() is True

def test_validate_accounting_balance(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    make_journal_df().to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    validator.validate_data_types()
    assert validator.validate_accounting_balance() is True

def test_validate_matching_consistency(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    make_journal_df().to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    validator.validate_data_types()
    validator.validate_accounting_balance()
    assert validator.validate_matching_consistency() is True

def test_validate_amount_consistency(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    make_journal_df().to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    validator.validate_data_types()
    validator.validate_accounting_balance()
    validator.validate_matching_consistency()
    assert validator.validate_amount_consistency() is True

def test_validate_duplicate_entries(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    # Add a duplicate entry
    df = make_journal_df()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    df.to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    validator.validate_data_types()
    validator.validate_accounting_balance()
    validator.validate_matching_consistency()
    validator.validate_amount_consistency()
    # Should fail due to duplicate
    assert validator.validate_duplicate_entries() is False
    assert any("Duplicate entries found" in e for e in validator.validation_results['errors'])

def test_run_all_validations_valid(tmp_path):
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    make_journal_df().to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    results = validator.run_all_validations()
    assert results['file_exists'] is True
    assert results['file_readable'] is True
    assert results['required_columns'] is True
    assert results['data_types'] is True
    assert results['accounting_balance'] is True
    assert results['matching_consistency'] is True
    assert results['duplicate_entries'] is True
    assert results['errors'] == []
    assert isinstance(validator.generate_report(), str)

def test_run_all_validations_invalid(tmp_path):
    # Missing required column
    journal_path = tmp_path / "journal.csv"
    match_path = tmp_path / "match.csv"
    df = make_journal_df().drop(columns=['amount'])
    df.to_csv(journal_path, index=False)
    make_match_suggestion_df().to_csv(match_path, index=False)
    validator = MatchingValidator(str(journal_path), str(match_path))
    results = validator.run_all_validations()
    assert results['required_columns'] is False
    assert any("Missing required columns" in e for e in results['errors']) 