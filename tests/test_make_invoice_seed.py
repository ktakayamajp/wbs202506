import os
import pandas as pd
import pytest
from src.data_processing import make_invoice_seed

def test_parse_billing_contracts_normal():
    file_path = "data/test/01_Project_Billing_Contracts_Varied_test.txt"
    projects = make_invoice_seed.parse_billing_contracts(file_path)
    assert isinstance(projects, list)
    assert len(projects) == 2
    assert projects[0]['project_id'] == 'PRJ_0001'
    assert projects[1]['billing_amount'] == 200000

def test_parse_billing_contracts_file_not_found():
    projects = make_invoice_seed.parse_billing_contracts("data/not_exist.txt")
    assert projects == []

def test_enrich_project_data_normal():
    projects = [
        {'project_id': 'PRJ_0001', 'client_name': 'A社', 'billing_year': '2024', 'billing_month': '06', 'billing_amount': 100000},
        {'project_id': 'PRJ_0002', 'client_name': 'B社', 'billing_year': '2024', 'billing_month': '06', 'billing_amount': 200000},
    ]
    master_path = "data/test/Project_master_test.csv"
    enriched = make_invoice_seed.enrich_project_data(projects, master_path)
    assert all('client_id' in p for p in enriched)
    assert enriched[0]['client_id'] == 'C001'
    assert enriched[1]['project_name'] == 'プロジェクトB'

def test_generate_invoice_seed(tmp_path):
    projects = [
        {'project_id': 'PRJ_0001', 'client_id': 'C001', 'client_name': 'A社', 'project_name': 'プロジェクトA', 'pm_id': 'PM01', 'billing_year': '2024', 'billing_month': '06', 'billing_amount': 100000},
        {'project_id': 'PRJ_0002', 'client_id': 'C002', 'client_name': 'B社', 'project_name': 'プロジェクトB', 'pm_id': 'PM02', 'billing_year': '2024', 'billing_month': '06', 'billing_amount': 200000},
    ]
    output_dir = tmp_path
    output_path = make_invoice_seed.generate_invoice_seed(projects, output_dir, yearmonth="202406")
    assert os.path.exists(output_path)
    df = pd.read_csv(output_path)
    assert len(df) == 2
    assert df['billing_amount'].sum() == 300000

def test_generate_invoice_seed_empty():
    output_path = make_invoice_seed.generate_invoice_seed([], "output/seed_test")
    assert output_path is None 