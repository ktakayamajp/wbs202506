import os
import pandas as pd
import pytest
from src.data_processing.invoice_seed_validator import InvoiceSeedValidator
from config.constants import YEAR_MIN, YEAR_MAX, MONTH_MIN, MONTH_MAX

def make_valid_seed_df():
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

def make_project_master_df():
    return pd.DataFrame([
        {'プロジェクトID': 'PRJ_0001', 'Client ID': 'Client_004', 'プロジェクト名称': 'プロジェクトA', 'プロジェクトマネージャID': 'ishida.kento'},
        {'プロジェクトID': 'PRJ_0002', 'Client ID': 'Client_001', 'プロジェクト名称': 'プロジェクトB', 'プロジェクトマネージャID': 'takahashi.misaki'}
    ])

def test_validate_file_exists_and_readable(tmp_path):
    df = make_valid_seed_df()
    file_path = tmp_path / "seed_test.csv"
    df.to_csv(file_path, index=False)
    validator = InvoiceSeedValidator(str(file_path))
    assert validator.validate_file_exists() is True
    assert validator.validate_file_readable() is True
    assert validator.df is not None

def test_validate_required_columns(tmp_path):
    df = make_valid_seed_df()
    file_path = tmp_path / "seed_test.csv"
    df.to_csv(file_path, index=False)
    validator = InvoiceSeedValidator(str(file_path))
    validator.validate_file_readable()
    assert validator.validate_required_columns() is True

def test_validate_data_types(tmp_path):
    df = make_valid_seed_df()
    file_path = tmp_path / "seed_test.csv"
    df.to_csv(file_path, index=False)
    validator = InvoiceSeedValidator(str(file_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    assert validator.validate_data_types() is True

def test_validate_duplicates(tmp_path):
    df = make_valid_seed_df()
    # Add a duplicate row for project_id
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    file_path = tmp_path / "seed_test.csv"
    df.to_csv(file_path, index=False)
    validator = InvoiceSeedValidator(str(file_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    validator.validate_data_types()
    # Should fail due to duplicate project_id
    assert validator.validate_duplicates() is False
    assert any("Duplicate project_ids" in e for e in validator.validation_results['errors'])

def test_validate_project_master_consistency(tmp_path, monkeypatch):
    df = make_valid_seed_df()
    file_path = tmp_path / "seed_test.csv"
    df.to_csv(file_path, index=False)
    master_df = make_project_master_df()
    master_path = tmp_path / "Project_master.csv"
    master_df.to_csv(master_path, index=False)
    import os as _os
    orig_exists = _os.path.exists
    orig_read_csv = pd.read_csv
    monkeypatch.setattr("os.path.exists", lambda p: True if str(master_path) in p else orig_exists(p))
    monkeypatch.setattr("pandas.read_csv", lambda p, *a, **k: master_df if str(master_path) in p else orig_read_csv(p, *a, **k))
    validator = InvoiceSeedValidator(str(file_path))
    validator.validate_file_readable()
    validator.validate_required_columns()
    validator.validate_data_types()
    validator.validate_duplicates()
    assert validator.validate_project_master_consistency() is True
    assert validator.validation_results['project_master_consistency'] is True

def test_run_all_validations_valid(tmp_path, monkeypatch):
    df = make_valid_seed_df()
    file_path = tmp_path / "seed_test.csv"
    df.to_csv(file_path, index=False)
    master_df = make_project_master_df()
    master_path = tmp_path / "Project_master.csv"
    master_df.to_csv(master_path, index=False)
    import os as _os
    orig_exists = _os.path.exists
    orig_read_csv = pd.read_csv
    monkeypatch.setattr("os.path.exists", lambda p: True if str(master_path) in p else orig_exists(p))
    monkeypatch.setattr("pandas.read_csv", lambda p, *a, **k: master_df if str(master_path) in p else orig_read_csv(p, *a, **k))
    validator = InvoiceSeedValidator(str(file_path))
    results = validator.run_all_validations()
    assert results['file_exists'] is True
    assert results['file_readable'] is True
    assert results['required_columns'] is True
    assert results['data_types'] is True
    assert results['duplicates'] is True
    assert results['errors'] == []
    assert isinstance(validator.generate_report(), str)

def test_run_all_validations_invalid(tmp_path):
    # Missing required column
    df = make_valid_seed_df().drop(columns=['billing_amount'])
    file_path = tmp_path / "seed_test.csv"
    df.to_csv(file_path, index=False)
    validator = InvoiceSeedValidator(str(file_path))
    results = validator.run_all_validations()
    assert results['required_columns'] is False
    assert any("Missing required columns" in e for e in results['errors']) 