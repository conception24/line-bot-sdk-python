# -*- coding: utf-8 -*-

import base64
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot.v3.webhook import WebhookParser  # ✅ 新SDKに対応
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)

app = Flask(__name__)

# チャネルシークレットとアクセストークンを環境変数から取得
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

# WebhookパーサーとAPIクライアント設定
parser = WebhookParser(channel_secret)
configuration = Configuration(access_token=channel_access_token)


def upload_to_drive(image_bytes, filename):
    # 環境変数からBase64の認証情報を復元
    credentials_json = base64.b64decode(os.environ['GOOGLE_CREDENTIALS_BASE64']).decode('utf-8')
    credentials_dict = json.loads(credentials_json)

    # 認証情報オブジェクトを作成
    creds = service_account.Credentials.from_service_account_info(credentials_dict)

    # Google Drive APIクライアントを初期化
    service = build('drive', 'v3', credentials=creds)

    # アップロードするファイルの設定
    file_metadata = {
        'name': filename,
        'parents': ['1PoDaKlXm788CXiHeTW9iEFGUwjlxVNBD']  # フォルダIDを指定
    }

    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype='image/jpeg')

    # アップロード実行
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return file.get('id')



# ✅ / にアクセスしたときの簡易応答（Render確認用）
@app.route("/")
def index():
    return "LINE Bot is alive."

# ✅ Webhook受け取りエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    for event in events:
        if not isinstance(event, MessageEvent):
            continue

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            # ✅ テキストメッセージの場合はそのままオウム返し
            if isinstance(event.message, TextMessageContent):
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=event.message.text)]
                    )
                )

            # ✅ 画像メッセージの場合は定型メッセージで応答
            elif isinstance(event.message, ImageMessageContent):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # LINEの画像を取得
        content_response = line_bot_api.get_message_content(message_id=event.message.id)
        image_bytes = b''.join(content_response.iter_content(chunk_size=1024))

        # Google Drive にアップロード
        file_id = upload_to_drive(image_bytes, f"{event.message.id}.jpg")

        # ユーザーに返信
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"画像を保存しました！（ID: {file_id}）")]
            )
        )


    return 'OK'

# ✅ アプリ起動（Render対応）
if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--debug] [--help]'
    )
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", debug=options.debug, port=port)
