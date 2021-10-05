from enum import unique
from types import MethodDescriptorType
from typing import Text
from flask import Flask, request, abort,render_template,make_response,redirect
from datetime import datetime 

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    PostbackEvent, PostbackTemplateAction, TemplateSendMessage,
    ButtonsTemplate, FollowEvent, MessageAction, RichMenu, RichMenuArea,
    RichMenuBounds, RichMenuSize, URIAction, actions, messages
)
from linebot.models.template import CarouselColumn, CarouselTemplate
from werkzeug.utils import validate_arguments
from unipa_automation import getInfoFromUnipa
import os
import json
import dotenv 
import requests
dotenv.load_dotenv("./data/.env")

app = Flask(__name__)
app.secret_key = os.environ["secret"]
# カレントディレクトリのenvfileを使用

UserID = os.environ["USERID"]
PassWord = os.environ["PASS"]
line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])



@app.route("/user/<user_id>")
def userlog(user_id):
    # 初めて使う場合のニックネームの設定
    resp= make_response(render_template('index.html',user=user_id))
    max_age= 60*60*24*3
    resp.set_cookie("usetId",value=str(user_id),max_age=max_age)
    return resp
    
# cookie取得
@app.route('/setcookie',methods=["POST"])
def setcookie():   
    # postされた値を取得
    user = request.form["userId"]
    pw = request.form["pass"]
    resp = make_response(render_template("read_cookie.html",user=user))
    max_age= 60*60*24*3
    expires = int(
        datetime.now().timestamp()) + max_age
    resp.set_cookie("user",value=str(user),max_age=max_age)
    resp.set_cookie("pass",value=str(pw),max_age=max_age)
    return resp

@app.route('/getcookie',methods=["GET"])
def getcookie():
    user = request.cookies.get("user")
    user_id = request.cookies.get("userId")
    line_bot_api.push_message(
        to=user_id,
        messages=TextSendMessage(text='OK!')
        )
    make_response(f'<h1>welcome  {user} </h1>')


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# メッセージを受け取った時のアクション
@handler.add(MessageEvent, message=TextMessage)
def send_infomation(event):
    user_id = event.source.user_id
    
    if event.message.text == '課題は？':
        df_rest = getInfoFromUnipa(userID=UserID, PassWord=PassWord)
        rest_list=["残りの課題はこちらです"]
        for _,v in df_rest.iterrows():
            kadai = v["課題名"]
            sime = v["課題提出終了日時"]
            state=v["ステータス"]
            rest_list.append(f"課題名 : {kadai}\n締切日 : {sime}\nステータス : {state}\n")
        rest_homework="\n".join(rest_list)
        line_bot_api.push_message(
        to=user_id,
        messages=TextSendMessage(text=rest_homework)
        )
    elif event.message.text=="ボタン":
        send_button(event=event,user_id=user_id)
    elif event.message.text=="イベント":
        show_carousel(user_id)
    else:
        line_bot_api.push_message(
            to=user_id,
            messages=TextSendMessage(text=event.message.text+"は理解不能")
        )

# 友達追加・ブロック解除時のアクション
@handler.add(FollowEvent)
def on_follow(event):
    return 

# ボタンなどの反応があった時のアクション
@handler.add(PostbackEvent)
def on_postback(event):
    reply_token = event.reply_token
    user_id = event.source.user_id
    postback_msg = event.postback.data

    if postback_msg == "is_show=1":
        line_bot_api.push_message(
            to=user_id,
            messages=TextSendMessage(text="is_showオプション1を選択")
        )
    elif postback_msg == "is_show=0":
        line_bot_api.push_message(
            to = user_id,
            messages=TextSendMessage(text="is_showオプション0を選択")
        )
    else:
        line_bot_api.push_message(
            to=user_id,
            messages=TextSendMessage(text=postback_msg)
        )

# これは単体で送るしかなさそう
def send_button(event,user_id):
    # ボタンテンプレートを作成

    message_template=ButtonsTemplate(
        text="Please select",
        title="select!",
        actions=[
            PostbackTemplateAction(
                label="ON",
                data="is_show=1"
            ),
            URIAction(
                label="get LOGIN!",
                uri=f"https://cef1-210-137-33-126.ngrok.io/user/{user_id}"
            )
        ]
    )
    # ボタンテンプレートを選択して送信
    line_bot_api.push_message(
        to=user_id,
        messages=TemplateSendMessage(
            alt_text="Buttons template",
            template=message_template
        )
    )
# カーセルのテスト
def show_carousel(user_id):
    # メッセージテンプレートの内容(collumn)を作成
    carousel_collumns=[
        CarouselColumn(
            text=value,
            title = value+"通知",
            actions=[
                PostbackTemplateAction(
                    label="ON",
                    data=value+"1",
                ),
                PostbackTemplateAction(
                    label="OFF",
                    data=value+"0",
                )
            ]
        ) for key,value in (zip(
            ("取引所","取引所","取引所","取引所","取引所"),
            ("Binance","kuCoin","Hupbipro","Ploniex","Bittrex")
        ))
    ]
    # メッセージテンプレート作成
    message_template = CarouselTemplate(columns=carousel_collumns)
    line_bot_api.push_message(
        to=user_id,
        messages=TemplateSendMessage(alt_text="carousel template",template=message_template)
    )   

def GetDisplayName():
    # ユーザーidを入手するためにapiをたたく
    access = os.environ["CHANNEL_ACCESS_TOKEN"]
    headers = {
        "Authorization": f"Bearer {access}"
    }

    response = requests.get(f"https://api.line.me/v2/bot/profile/{user_id}",headers=headers)
    print(response.json)    

if __name__ == "__main__":
    app.run(port=8000)