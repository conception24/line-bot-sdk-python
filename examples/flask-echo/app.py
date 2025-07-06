# -*- coding: utf-8 -*-

import base64
import json
import io
import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    ImageMessage,
    TextSendMessage
)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)

# 環境変数からLINEのチャネル情報を取得
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

if channel_secret is None or channel_access_token is None:
    print("環境変数が設定されていません。")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# ✅ Google Driveにアップロードする関数
def upload_to_drive(image_bytes, filename):
    credentials_json = base64.b64decode(os.environ['GOOGLE_CREDENTIALS_BASE64']).decode('utf-8')
    credentials_dict = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(credentials_dict)

    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': filename,
        'parents': ['1PoDaKlXm788CXiHeTW9iEFGUwjlxVNBD']  # あなたのDriveフォルダID
    }

    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype='image/jpeg')

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return file.get('id')

# ✅ 動作確認用ルート
@app.route("/")
def index():
    return "LINE Bot is alive."

# ✅ Webhookエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    if isinstance(event.message, TextMessage):
        # テキストメッセージ：オウム返し
        reply_text = event.message.text
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

    elif isinstance(event.message, ImageMessage):
        # 画像メッセージ：保存して返信
        message_content = line_bot_api.get_message_content(event.message.id)
        image_bytes = b''.join(message_content.iter_content())

        file_id = upload_to_drive(image_bytes, f"{event.message.id}.jpg")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"画像を保存しました！（ID: {file_id}）")
        )

# ✅ アプリ起動設定（Render対応）
if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", debug=options.debug, port=port)
