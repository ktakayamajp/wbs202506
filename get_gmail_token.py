#!/usr/bin/env python3
"""
Gmail API リフレッシュトークン取得スクリプト
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Gmail APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_refresh_token():
    """Gmail APIのリフレッシュトークンを取得"""
    
    creds = None
    token_path = 'data/gmail_token.json'
    credentials_path = 'data/gmail_credentials.json'
    
    # 既存のトークンファイルをチェック
    if os.path.exists(token_path):
        print("既存のトークンファイルが見つかりました。")
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # トークンが無効または期限切れの場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("トークンを更新しています...")
            creds.refresh(Request())
        else:
            print("新しい認証フローを開始します...")
            
            # 認証情報ファイルの存在確認
            if not os.path.exists(credentials_path):
                print(f"❌ 認証情報ファイルが見つかりません: {credentials_path}")
                print("\n以下の手順で認証情報を取得してください:")
                print("1. Google Cloud Console (https://console.cloud.google.com/) にアクセス")
                print("2. プロジェクトを作成または選択")
                print("3. Gmail APIを有効化")
                print("4. OAuth 2.0クライアントIDを作成（デスクトップアプリケーション）")
                print("5. JSONファイルをダウンロード")
                print(f"6. ダウンロードしたファイルを {credentials_path} として保存")
                print("\n注意: アプリケーションの種類は必ず「デスクトップアプリケーション」を選択してください")
                return None
            
            try:
                # 認証フローの実行（固定ポートを使用）
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                print("ブラウザが開きます。GoogleアカウントでログインしてGmailへのアクセスを許可してください。")
                creds = flow.run_local_server(port=8080, prompt='consent')
            except Exception as e:
                print(f"認証フローでエラーが発生しました: {e}")
                print("\n解決方法:")
                print("1. Google Cloud ConsoleでOAuth 2.0クライアントIDの設定を確認")
                print("2. アプリケーションの種類が「デスクトップアプリケーション」になっているか確認")
                print("3. 必要に応じて新しいOAuth 2.0クライアントIDを作成")
                return None
        
        # トークンを保存
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        
        print(f"✅ トークンファイルを保存しました: {token_path}")
    
    # 認証情報の表示
    print("\n=== Gmail API 認証情報 ===")
    print(f"Client ID: {creds.client_id}")
    print(f"Client Secret: {creds.client_secret}")
    print(f"Refresh Token: {creds.refresh_token}")
    print(f"Token URI: {creds.token_uri}")
    print(f"Scopes: {creds.scopes}")
    
    # .envファイル用の設定値を表示
    print("\n=== .envファイル用設定値 ===")
    print(f"GMAIL_CLIENT_ID={creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print(f"GMAIL_SENDER={creds.client_id.split('.')[0]}@gmail.com")
    
    return creds

def update_env_file(creds):
    """環境変数ファイルを更新"""
    env_path = '.env'
    
    if not os.path.exists(env_path):
        print(f"❌ .envファイルが見つかりません: {env_path}")
        return False
    
    # .envファイルを読み込み
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 認証情報を更新
    updated_lines = []
    for line in lines:
        if line.startswith('GMAIL_CLIENT_ID='):
            updated_lines.append(f'GMAIL_CLIENT_ID={creds.client_id}\n')
        elif line.startswith('GMAIL_CLIENT_SECRET='):
            updated_lines.append(f'GMAIL_CLIENT_SECRET={creds.client_secret}\n')
        elif line.startswith('GMAIL_REFRESH_TOKEN='):
            updated_lines.append(f'GMAIL_REFRESH_TOKEN={creds.refresh_token}\n')
        elif line.startswith('GMAIL_SENDER='):
            # デフォルトの送信者メールアドレスを設定
            sender_email = f"{creds.client_id.split('.')[0]}@gmail.com"
            updated_lines.append(f'GMAIL_SENDER={sender_email}\n')
        else:
            updated_lines.append(line)
    
    # .envファイルを更新
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print(f"✅ .envファイルを更新しました: {env_path}")
    return True

def main():
    """メイン処理"""
    print("Gmail API リフレッシュトークン取得ツール")
    print("=" * 50)
    
    try:
        # リフレッシュトークンを取得
        creds = get_gmail_refresh_token()
        
        if creds:
            # .envファイルを更新
            update_env_file(creds)
            
            print("\n✅ 認証情報の取得が完了しました！")
            print("\n次のステップ:")
            print("1. .envファイルのGMAIL_SENDERを実際のGmailアドレスに変更")
            print("2. python src/email/invoice_email_sender.py でテスト実行")
        else:
            print("\n❌ 認証情報の取得に失敗しました。")
            print("上記の手順に従って認証情報を設定してください。")
    
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("認証情報ファイルが正しく設定されているか確認してください。")

if __name__ == "__main__":
    main() 