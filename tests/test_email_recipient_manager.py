from src.email_utils.email_recipient_manager import EmailRecipientManager
import sys
import os
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '../..')))

if __name__ == "__main__":
    manager = EmailRecipientManager()
    print("=== デフォルト受信者 ===")
    for r in manager.get_recipients():
        print(vars(r))
    print("=== PRJ_0001 受信者 ===")
    for r in manager.get_recipients("PRJ_0001"):
        print(vars(r))
    print("=== CC ===")
    for r in manager.get_cc_recipients():
        print(vars(r))
    print("=== BCC ===")
    for r in manager.get_bcc_recipients():
        print(vars(r))
