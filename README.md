# Todoリストアプリ

Python (Flask) + Google スプレッドシートで動くTodoリストWebアプリ。
デザインは [Royal Canin Design Language](https://developer.royalcanin.com/) を参考にしています。

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/デザイン仕様書.md](docs/デザイン仕様書.md) | RCDL調査に基づくデザイントークン・コンポーネント仕様 |
| [docs/要件定義書.md](docs/要件定義書.md) | 機能要件・画面要件・データ仕様・非機能要件 |
| [SETUP.md](SETUP.md) | ローカル起動 / Google Sheets接続 / サーバー公開手順 |

## 機能

- やることの登録・編集（タイトル / 内容 / 期日）
- 一覧表示（未完了→完了、期日昇順）
- 完了/未完了の切替、削除、期限超過の強調表示
- データはGoogle スプレッドシートに保存（未設定時はローカルJSONで動作）

## クイックスタート

```bash
pip install -r requirements.txt
python app.py
```

http://localhost:5000 を開く。Google Sheets接続と公開手順は [SETUP.md](SETUP.md) を参照。

## 構成

```
app.py            # Flaskアプリ（ルーティング・バリデーション）
storage.py        # 永続化層（SheetsStore / LocalStore）
templates/        # Jinja2テンプレート
static/css/       # RCDL準拠のデザイントークンCSS
render.yaml       # Render用デプロイ設定
Procfile          # Heroku系PaaS用
```
