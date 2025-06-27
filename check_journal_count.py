import pandas as pd

# 最新の仕訳ファイルを読み込み
df = pd.read_csv('output/journal/journal_20250624_001056.csv')

print("=== 入金マッチング出力件数確認 ===")
print(f"仕訳エントリ総数: {len(df)}")
print(f"入金仕訳件数: {len(df[df['entry_type'] == 'cash_receipt'])}")
print(f"売上仕訳件数: {len(df[df['entry_type'] == 'revenue_recognition'])}")
print(f"手動確認件数: {len(df[df['entry_type'] == 'manual_review'])}")
print(f"総金額: {df['amount'].sum():,} 円")

# マッチング提案ファイルとの比較
match_df = pd.read_csv('output/ai_output/match_suggestion_202401.csv')
print(f"\n=== マッチング提案との比較 ===")
print(f"マッチング提案件数: {len(match_df)}")
print(f"マッチング提案総額: {match_df['amount'].sum():,} 円")

# 各取引IDの件数確認
unique_transactions = df['transaction_id'].nunique()
print(f"\n=== 取引ID別件数 ===")
print(f"ユニーク取引ID数: {unique_transactions}")

# 各取引IDごとの仕訳件数
txn_counts = df.groupby('transaction_id').size()
print(f"取引ID別仕訳件数:")
for txn_id, count in txn_counts.items():
    print(f"  {txn_id}: {count}件")

# 金額の整合性チェック
print(f"\n=== 金額整合性チェック ===")
cash_amount = df[df['entry_type'] == 'cash_receipt']['amount'].sum()
revenue_amount = df[df['entry_type'] == 'revenue_recognition']['amount'].sum()
print(f"入金仕訳総額: {cash_amount:,} 円")
print(f"売上仕訳総額: {revenue_amount:,} 円")
print(f"金額差: {abs(cash_amount - revenue_amount):,} 円")
print(f"金額一致: {'✅' if cash_amount == revenue_amount else '❌'}")

# マッチング提案との金額比較
match_amount = match_df['matched_amount'].sum()
print(f"\nマッチング提案マッチ金額: {match_amount:,} 円")
print(f"仕訳金額との差: {abs(cash_amount - match_amount):,} 円")
print(f"金額一致: {'✅' if cash_amount == match_amount else '❌'}") 