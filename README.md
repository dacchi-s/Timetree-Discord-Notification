# TimeTree to Discord Notification Script

TimeTreeカレンダーの予定を取得し、DiscordのWebhookを使って通知するPythonスクリプトです。

## 作ったモチベーション

TimeTreeはUI/UXに優れたカレンダーアプリですが、**公式APIが用意されていません**。また、TimeTreeで予定を共有しても通知を見落として予定を飛ばしてしまうことがありました（笑）。

そこで、TimeTreeの予定を毎日Discordに自動通知する仕組みを作ることで、予定を確実に把握できるようにしました。

## 機能

- **毎日**: 今日と明日の予定を通知
- 予定がない場合は「予定はありません」と明示
- TimeTreeへのログイン認証（内部API使用）
- 終日・時間指定の予定に対応
- 日本語の日付フォーマット

## 前提条件

- Python 3.9以上
- TimeTreeアカウント
- Discord Webhook URL

## セットアップ（Raspberry Pi）

### 1. ファイルの配置

```bash
cd /home/pi
mkdir -p timetree-discord
cd timetree-discord

# ファイルを配置（scp等で転送してください）
```

### 2. 仮想環境の構築

```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate

# 依存パッケージのインストール
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env.example` をコピーして `.env` を作成：

```bash
cp .env.example .env
```

`.env` ファイルを編集して認証情報を設定：

```env
TIMETREE_EMAIL=your_email@example.com
TIMETREE_PASSWORD=your_password
TIMETREE_CALENDAR_ID=          # オプション（空欄の場合、最初のカレンダーを使用）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### カレンダーIDの確認方法

```bash
# カレンダー一覧を表示
./venv/bin/python main.py --list
```

#### Discord Webhook URLの取得方法

1. Discordサーバーで通知したいチャンネルの「チャンネル設定」を開く
2. 「連携サービス」→「Webhook」を選択
3. 「新しいWebhook」を作成
4. Webhook URLをコピーして `.env` に貼り付け

## 使い方

### 手動実行

```bash
# 今日の予定を通知
./venv/bin/python main.py

# カレンダー一覧を表示
./venv/bin/python main.py --list
```

### cronで定期実行

毎日朝6時に実行する場合：

```bash
# crontabを編集
crontab -e

# 以下の行を追加（仮想環境を使用）
0 6 * * * cd /home/pi/timetree-discord && /home/pi/timetree-discord/venv/bin/python main.py >> timetree_discord.log 2>&1
```

crontabの設定例：

| 時刻 | 設定値 |
|------|--------|
| 毎日6時 | `0 6 * * *` |
| 毎日朝8時 | `0 8 * * *` |
| 毎週月曜9時 | `0 9 * * 1` |

ログの確認：

```bash
tail -f timetree_discord.log
```

## 通知フォーマット

### 予定がある場合

```
📅 今日の予定 - 1月31日 (金)

予定
• 14:00 - 16:00 ミーティング
  📍 会議室A
• 18:00 - 夕食の予定

📅 明日の予定 - 2月1日 (土)

予定
• 終日 - 誕生日パーティー
```

### 予定がない場合

```
📅 今日の予定 - 2月1日 (土)

予定はありません

📅 明日の予定 - 2月2日 (日)

予定はありません
```

## ファイル構成

| ファイル | 説明 |
|---------|------|
| `main.py` | メインスクリプト |
| `timetree_scraper.py` | TimeTreeからのデータ取得処理 |
| `discord_notifier.py` | Discord Webhookへの通知処理 |
| `requirements.txt` | Python依存パッケージ |
| `.env` | 認証情報（git管理外） |
| `.env.example` | 環境変数のテンプレート |

## トラブルシューティング

### ログインに失敗する

- メールアドレスとパスワードが正しいか確認
- TimeTreeのWebサイトで直接ログインできるか確認

### カレンダーが見つからない

- `TIMETREE_CALENDAR_ID` を空欄にすると、最初のカレンダーが自動選択されます
- `python main.py --list` で正しいカレンダーIDを確認できます

### Discordに通知が来ない

- Webhook URLが正しいか確認
- Webhookが設定されたチャンネルが存在するか確認
- ログを確認してエラー内容をチェック

## セキュリティ上の注意

- `.env` ファイルにはパスワードが含まれているため、絶対にgit commitしないでください（`.gitignore`に含まれています）
- このスクリプトはTimeTreeの内部APIを使用しているため、仕様変更により動作しなくなる可能性があります

## ライセンス

MIT License

## 免責事項

このスクリプトは非公式のものです。TimeTreeのサービス利用規約に違反しないようご使用ください。

---

# TimeTree to Discord Notification Script (English)

**A Python script that fetches TimeTree calendar events and sends notifications via Discord Webhooks.**

## Motivation

TimeTree has excellent UI/UX, but **it lacks an official API**. Also, even when sharing events on TimeTree, notifications can be overlooked, causing me to miss scheduled events (lol).

So I created this system to automatically send daily TimeTree event notifications to Discord, ensuring I never miss a schedule again.

## Features

- **Daily**: Sends notifications for today's and tomorrow's events
- Clearly states "No events" when the schedule is empty
- TimeTree login authentication (using internal API)
- Supports all-day and time-specific events
- Japanese date format

## Prerequisites

- Python 3.9 or higher
- TimeTree account
- Discord Webhook URL

## Setup (Raspberry Pi)

### 1. File Placement

```bash
cd /home/pi
mkdir -p timetree-discord
cd timetree-discord

# Place files (transfer via scp or similar)
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables

Copy `.env.example` to create `.env`:

```bash
cp .env.example .env
```

Edit `.env` to set your credentials:

```env
TIMETREE_EMAIL=your_email@example.com
TIMETREE_PASSWORD=your_password
TIMETREE_CALENDAR_ID=          # Optional (leave blank to use first calendar)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### How to Find Calendar ID

```bash
# List calendars
./venv/bin/python main.py --list
```

#### How to Get Discord Webhook URL

1. Open "Channel Settings" for the target channel on your Discord server
2. Go to "Integrations" → "Webhooks"
3. Create "New Webhook"
4. Copy the Webhook URL and paste it into `.env`

## Usage

### Manual Execution

```bash
# Send today's events
./venv/bin/python main.py

# List calendars
./venv/bin/python main.py --list
```

### Automated Execution with cron

To run every day at 6 AM:

```bash
# Edit crontab
crontab -e

# Add the following line (using virtual environment)
0 6 * * * cd /home/pi/timetree-discord && /home/pi/timetree-discord/venv/bin/python main.py >> timetree_discord.log 2>&1
```

Crontab examples:

| Time | Setting |
|------|---------|
| Daily at 6 AM | `0 6 * * *` |
| Daily at 8 AM | `0 8 * * *` |
| Every Monday at 9 AM | `0 9 * * 1` |

Check logs:

```bash
tail -f timetree_discord.log
```

## Notification Format

### When Events Exist

```
📅 今日の予定 - Jan 31 (Fri)

Events
• 14:00 - 16:00 Meeting
  📍 Room A
• 18:00 - Dinner

📅 明日の予定 - Feb 1 (Sat)

Events
• All Day - Birthday Party
```

### When No Events

```
📅 今日の予定 - Feb 1 (Sat)

No events

📅 明日の予定 - Feb 2 (Sun)

No events
```

## File Structure

| File | Description |
|------|-------------|
| `main.py` | Main script |
| `timetree_scraper.py` | TimeTree data fetching |
| `discord_notifier.py` | Discord Webhook notification |
| `requirements.txt` | Python dependencies |
| `.env` | Credentials (not in git) |
| `.env.example` | Environment variable template |

## Troubleshooting

### Login Fails

- Verify email and password are correct
- Check if you can log in directly on TimeTree website

### Calendar Not Found

- Leave `TIMETREE_CALENDAR_ID` blank to auto-select first calendar
- Use `python main.py --list` to find correct calendar ID

### Discord Notifications Not Appearing

- Verify Webhook URL is correct
- Check the channel with Webhook still exists
- Check logs for error details

## Security Notes

- `.env` file contains passwords and should never be git committed (included in `.gitignore`)
- This script uses TimeTree's internal API, which may break if TimeTree changes their specifications

## License

MIT License

## Disclaimer

This script is unofficial. Please use responsibly and in accordance with TimeTree's terms of service.
