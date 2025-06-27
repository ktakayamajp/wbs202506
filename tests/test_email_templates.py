import pytest
from src.email_utils.email_templates import EmailTemplateManager

def test_get_template_names():
    manager = EmailTemplateManager()
    for name in [
        'invoice_notification',
        'approval_request',
        'approval_reminder',
        'payment_confirmation',
        'system_notification',
        'error_notification',
    ]:
        template = manager.get_template(name)
        assert template is not None
        assert hasattr(template, 'subject')
        assert hasattr(template, 'html_body')
        assert hasattr(template, 'text_body')

def test_render_template_variable_replacement():
    manager = EmailTemplateManager()
    context = {
        'project_name': 'プロジェクトA',
        'billing_period': '2024年6月',
        'billing_amount': '100000',
        'due_date': '2024-07-31',
        'recipient_name': '山田太郎',
        'custom_message': '備考テスト',
    }
    rendered = manager.render_template('invoice_notification', context)
    assert rendered is not None
    for v in context.values():
        assert v in rendered.subject or v in rendered.html_body or v in rendered.text_body

def test_render_template_missing_template():
    manager = EmailTemplateManager()
    rendered = manager.render_template('not_exist', {'foo': 'bar'})
    assert rendered is None

def test_render_template_missing_context():
    manager = EmailTemplateManager()
    # Only provide some variables
    context = {'project_name': 'プロジェクトA'}
    rendered = manager.render_template('invoice_notification', context)
    assert rendered is not None
    # Unreplaced placeholders should remain
    assert '{{ billing_period }}' in rendered.subject or '{{ billing_period }}' in rendered.html_body

def test_render_template_extra_context():
    manager = EmailTemplateManager()
    context = {
        'project_name': 'プロジェクトA',
        'billing_period': '2024年6月',
        'billing_amount': '100000',
        'due_date': '2024-07-31',
        'recipient_name': '山田太郎',
        'custom_message': '備考テスト',
        'extra_var': 'should_be_ignored',
    }
    rendered = manager.render_template('invoice_notification', context)
    assert rendered is not None
    assert 'should_be_ignored' not in rendered.subject 