from flask import Flask, request, jsonify
import json
from src.notifications.approval_workflow import ApprovalWorkflowManager, ApprovalStatus
from src.notifications.slack_notifier import SlackNotifier, InvoiceApprovalRequest
from src.email_utils.invoice_email_sender import GmailEmailSender, InvoiceEmailData, EmailRecipient

app = Flask(__name__)

workflow_manager = ApprovalWorkflowManager()
slack_notifier = SlackNotifier()
email_sender = GmailEmailSender()

def approval_to_invoice_approval_request(approval):
    return InvoiceApprovalRequest(
        invoice_id=approval.invoice_id,
        project_id=approval.project_id,
        client_name=approval.client_name,
        project_name=approval.project_name,
        billing_amount=approval.billing_amount,
        pdf_path=approval.pdf_path,
        requestor=approval.requestor,
        due_date=approval.due_date,
        priority=approval.priority.value if hasattr(approval.priority, 'value') else str(approval.priority)
    )

@app.route("/slack/actions", methods=["POST"])
def slack_actions():
    payload = json.loads(request.form["payload"])
    action = payload["actions"][0]
    action_id = action["action_id"]
    value = action["value"]
    user = payload["user"]["username"]
    response_url = payload["response_url"]

    invoice_id = value.split("_", 1)[1]
    request_id = invoice_id  # 仮: invoice_id = request_id

    if action_id == "approve_invoice":
        workflow_manager.update_approval_status(request_id, ApprovalStatus.APPROVED, user)
        approval = workflow_manager.get_approval_request(request_id)
        if approval:
            recipient = EmailRecipient(
                email="kanji.takayama@gmail.com",  # 実際の宛先に変更
                name=approval.requestor,
                company=approval.client_name
            )
            email_data = InvoiceEmailData(
                invoice_id=approval.invoice_id,
                project_id=approval.project_id,
                client_name=approval.client_name,
                project_name=approval.project_name,
                billing_amount=approval.billing_amount,
                billing_period="2025年6月",
                due_date=approval.due_date.strftime("%Y年%m月%d日"),
                pdf_path=approval.pdf_path,
                recipient=recipient,
                custom_message="承認されました。"
            )
            email_sender.send_invoice_email(email_data)
            slack_notifier.send_approval_result_notification(
                approval_to_invoice_approval_request(approval), "approved", user)
        return jsonify({"text": "✅ 承認しました。請求書メールを送信します。"})
    elif action_id == "reject_invoice":
        workflow_manager.update_approval_status(request_id, ApprovalStatus.REJECTED, user)
        approval = workflow_manager.get_approval_request(request_id)
        if approval:
            slack_notifier.send_approval_result_notification(
                approval_to_invoice_approval_request(approval), "rejected", user)
        return jsonify({"text": "❌ 却下しました。"})
    else:
        return jsonify({"text": "未対応のアクションです。"})

if __name__ == "__main__":
    app.run(port=5000, debug=True) 