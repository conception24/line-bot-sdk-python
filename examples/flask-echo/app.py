# -*- coding: utf-8 -*-
import os
import sys
import logging
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

# ✅ ログ設定を追加
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 環境変数からLINEのチャネル情報を取得
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

# ✅ 環境変数の確認ログを追加
logger.info("=== 環境変数チェック ===")
logger.info(f"Channel Secret: {'設定済み' if channel_secret else '未設定'}")
logger.info(f"Access Token: {'設定済み' if channel_access_token else '未設定'}")

if channel_secret is None or channel_access_token is None:
    logger.error("環境変数が設定されていません。")
    print("環境変数が設定されていません。")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# ✅ 動作確認用ルート
@app.route("/")
def index():
    logger.info("/ エンドポイントにアクセスされました")
    return "LINE Bot is alive."

# ✅ Webhookエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    logger.info("=== Webhook受信 ===")
    
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    logger.info(f"署名: {signature[:10]}..." if signature else "署名なし")
    logger.info(f"ボディ長: {len(body)} 文字")
    
    try:
        handler.handle(body, signature)
        logger.info("メッセージ処理完了")
    except InvalidSignatureError:
        logger.error("署名検証エラー - Channel Secretが間違っている可能性があります")
        abort(400)
    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        abort(500)
    
    return 'OK'

# ✅ ユーザーからのメッセージ処理（Text / Image）
@handler.add(MessageEvent)
def handle_message(event):
    logger.info("=== メッセージ受信 ===")
    logger.info(f"イベントタイプ: {type(event.message)}")
    
    if isinstance(event.message, TextMessage):
        logger.info(f"テキストメッセージ: {event.message.text}")
        
        try:
            # テキストメッセージ：オウム返し
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=event.message.text)
            )
            logger.info("テキストメッセージ返信完了")
            
        except Exception as e:
            logger.error(f"テキストメッセージ返信エラー: {str(e)}")
    
    elif isinstance(event.message, ImageMessage):
        logger.info("画像メッセージを受信")

        try:
            # 画像データを取得してBytesIOに格納
            from io import BytesIO
            message_id = event.message.id
            message_content = line_bot_api.get_message_content(message_id)
            
            image_data = BytesIO()
            for chunk in message_content.iter_content():
                image_data.write(chunk)
            image_data.seek(0)

            logger.info("画像データをBytesIOに保存完了")

            # 仮返信
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="画像を受け取りました！")
            )
            logger.info("画像メッセージ返信完了")

        except Exception as e:
            logger.error(f"画像処理エラー: {str(e)}")
    
    else:
        logger.info(f"未対応のメッセージタイプ: {type(event.message)}")


# ✅ アプリ起動設定（Render対応）
if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()
    port = int(os.environ.get("PORT", 10000))
    
    logger.info(f"=== アプリ起動 ===")
    logger.info(f"ポート: {port}")
    logger.info(f"デバッグモード: {options.debug}")
    
    app.run(host="0.0.0.0", debug=options.debug, port=port)
