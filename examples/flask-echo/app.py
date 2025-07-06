# -*- coding: utf-8 -*-

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

app = Flask(__name__)

# 環境変数からLINEのチャネル情報を取得
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

if channel_secret is None or channel_access_token is None:
    print("環境変数が設定されていません。")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

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
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text)
        )

    elif isinstance(event.message, ImageMessage):
        # 画像メッセージ：「画像ありがとう！」と返信（保存はしない）
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="画像ありがとう！")
        )

# ✅ アプリ起動設定（Render対応）
if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", debug=options.debug, port=port)
