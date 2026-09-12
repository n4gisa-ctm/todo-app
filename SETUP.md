# セットアップ・公開手順

## 1. ローカルで動かす

```powershell
cd "C:\Users\user\Desktop\to do"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

http://localhost:5000 を開く。

Google スプレッドシート未設定の間は `data/todos.json` に保存される「開発モード」で動作します
（画面上部に通知が出ます）。

## 2. Google スプレッドシートに接続する

### 2-1. サービスアカウントを作成

1. [Google Cloud Console](https://console.cloud.google.com/) にログインし、プロジェクトを作成（既存でも可）。
2. 「APIとサービス」→「ライブラリ」から **Google Sheets API** を検索して「有効にする」。
3. 「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」。
   - 名前は任意（例: `todo-app`）。ロールは不要（スキップでOK）。
4. 作成したサービスアカウントを開き、「キー」タブ →「鍵を追加」→「新しい鍵を作成」→ **JSON**。
   - ダウンロードされたJSONファイルをこのフォルダに `service_account.json` という名前で保存。
   - ⚠️ このファイルは秘密情報です。Gitにコミットしない（.gitignore済み）。

### 2-2. スプレッドシートを用意して共有

1. [Google スプレッドシート](https://sheets.google.com) で新規スプレッドシートを作成（名前は任意）。
2. `service_account.json` 内の `client_email` の値（`xxx@xxx.iam.gserviceaccount.com`）をコピー。
3. スプレッドシートの「共有」で、そのメールアドレスを**編集者**として追加。
4. スプレッドシートのURLからIDを控える:
   `https://docs.google.com/spreadsheets/d/`**`ここがID`**`/edit`

※ `todos` ワークシートとヘッダー行はアプリが初回接続時に自動作成します。

### 2-3. 環境変数を設定

`.env.example` をコピーして `.env` を作り、値を設定:

```
SECRET_KEY=ランダムな文字列
SPREADSHEET_ID=控えたID
GOOGLE_CREDENTIALS_JSON=service_account.json
```

アプリを再起動すると、開発モードの通知が消えてスプレッドシート保存に切り替わります。

## 3. サーバーで公開する（Render 無料プラン）

1. このフォルダをGitHubリポジトリにpushする（`service_account.json` と `.env` は含めない）。
2. [Render](https://render.com) にサインアップ → 「New」→「Web Service」→ リポジトリを接続。
   - `render.yaml` を自動検出、または手動設定:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn app:app`
3. 環境変数を設定（Environment タブ）:
   - `SECRET_KEY` … ランダム文字列
   - `SPREADSHEET_ID` … スプレッドシートのID
   - `GOOGLE_CREDENTIALS_JSON` … **`service_account.json` の中身（JSON文字列全体）をそのまま貼り付け**
4. デプロイ完了後、発行されたURL（`https://todo-app-xxxx.onrender.com`）で公開されます。

> 他のPaaS（Railway, Fly.io, PythonAnywhere等）でも同じ環境変数を設定すれば動作します。
> Heroku系のプラットフォーム向けに `Procfile` も同梱しています。

## 4. 環境変数一覧

| 変数 | 必須 | 内容 |
|---|---|---|
| `SECRET_KEY` | 推奨 | Flaskのセッション秘密鍵 |
| `SPREADSHEET_ID` | Sheets利用時 | 保存先スプレッドシートのID |
| `GOOGLE_CREDENTIALS_JSON` | Sheets利用時 | サービスアカウントJSONのパス、または中身の文字列 |
