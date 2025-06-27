import os
import pytest
from src.pdf_generation.build_invoice_pdf import InvoicePDFGenerator

def test_load_draft_invoice_data():
    generator = InvoicePDFGenerator()
    draft_file = "output/ai_output/draft_invoice_test.json"
    data = generator.load_draft_invoice_data(draft_file)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['project_id'] == 'PRJ_0001'

def test_load_draft_invoice_data_file_not_found():
    generator = InvoicePDFGenerator()
    with pytest.raises(Exception):
        generator.load_draft_invoice_data("output/ai_output/not_exist.json")

def test_validate_draft_data():
    generator = InvoicePDFGenerator()
    valid_data = [
        {'project_id': 'PRJ_0001', 'client_name': 'A社', 'project_name': 'プロジェクトA', 'billing_amount': 100000},
        {'project_id': 'PRJ_0002', 'client_name': 'B社', 'project_name': 'プロジェクトB', 'billing_amount': 200000},
    ]
    assert generator.validate_draft_data(valid_data) is True
    invalid_data = [
        {'project_id': 'PRJ_0001', 'client_name': 'A社', 'billing_amount': 100000},  # project_name欠如
    ]
    assert generator.validate_draft_data(invalid_data) is False

def test_prepare_invoice_context():
    generator = InvoicePDFGenerator()
    invoice_data = {'project_id': 'PRJ_0001', 'client_name': 'A社', 'project_name': 'プロジェクトA', 'billing_amount': 100000}
    company_info = {'name': 'テスト株式会社', 'address': '東京都', 'phone': '03-0000-0000', 'email': 'test@example.com'}
    context = generator.prepare_invoice_context(invoice_data, company_info)
    assert 'company_name' in context
    assert 'invoice_data' in context
    assert context['invoice_data']['client_name'] == 'A社'

def test_generate_html_content():
    generator = InvoicePDFGenerator()
    invoice_data = {'project_id': 'PRJ_0001', 'client_name': 'A社', 'project_name': 'プロジェクトA', 'billing_amount': 100000}
    company_info = {'name': 'テスト株式会社', 'address': '東京都', 'phone': '03-0000-0000', 'email': 'test@example.com'}
    context = generator.prepare_invoice_context(invoice_data, company_info)
    html = generator.generate_html_content(context)
    assert isinstance(html, str)
    assert 'A社' in html

def test_generate_pdf_from_html(tmp_path):
    generator = InvoicePDFGenerator()
    invoice_data = {'project_id': 'PRJ_0001', 'client_name': 'A社', 'project_name': 'プロジェクトA', 'billing_amount': 100000}
    company_info = {'name': 'テスト株式会社', 'address': '東京都', 'phone': '03-0000-0000', 'email': 'test@example.com'}
    context = generator.prepare_invoice_context(invoice_data, company_info)
    html = generator.generate_html_content(context)
    output_path = os.path.join(tmp_path, "test_invoice.pdf")
    result = generator.generate_pdf_from_html(html, output_path)
    assert result is True
    assert os.path.exists(output_path) 