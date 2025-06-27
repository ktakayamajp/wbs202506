# Data Directory Structure

This directory contains data files used by the project. Files are organized as follows:

## Production/Reference Data (this directory)
- `Updated_Accounts_Receivable.csv`
- `03_Bank_Data_Final.csv`
- `01_Project_Billing_Contracts_Varied.txt`
- `02_請求書_テンプレート_003.xlsx`
- `Client_Master.csv`
- `Payment_Classification_Answer.csv`
- `Project_master.csv`
- `email_recipients.json`
- `approval_workflow.db`
- `gmail_token.json`, `gmail_credentials.json`
- `email_recipients.example.json` (example/sample)

## Test Data (`data/test/`)
- `Updated_Accounts_Receivable_test.csv`
- `bank_test.csv`
- `01_Project_Billing_Contracts_Varied_test.txt`
- `Project_master_test.csv`

Test data is used for unit/integration testing and should not be used in production workflows.

---
If you add new test data, please place it in the `data/test/` directory and name it clearly (e.g., with `_test` in the filename). 