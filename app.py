from flask import Flask
app = Flask(__name__)

from flask import request, abort, render_template
from linebot import  LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

import speech_recognition as sr
from pydub import AudioSegment
import os

import datetime
from urllib.parse import parse_qsl

import json
f = open("data.json")
comm_json = json.load(f)
v = open("variables.json")
var_json = json.load(v)
p = open("people.json")
people_json = json.load(p)

is_record = False
is_entering = False

line_bot_api = LineBotApi('n0GThW+dzgtzOKw0aaiVt5mdkOVt36Ts9U6qRjSHzYU818SCSN0llBsdZ6TOFIm++AEGFZgwnYsAo0dMErjSrvI0ar+jt+F4Sx63InLgXeL7mZuTsw5lRpv7AWSuS0uN67yCJodkr9E/x7TpJgAyUgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('2b3d7b7bf941da91bf6b6d6352fe5af4')

liffid="2000498096-XzeBzlB5"

@app.route("/page")
def page():
    return render_template('index.html', liffid=liffid)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=AudioMessage)  # 取得聲音時做的事情
def handle_message_Audio(event):
    is_record = var_json["is_record"]
    is_entering = var_json["is_entering"]
    if not is_record:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="目前不是錄音相關環節"))
        return
    
    try:
        #接收使用者語音訊息並存檔
        print(event.source)
        UserID = event.source.user_id
        path="./audio/"+UserID+".wav"
        audio_content = line_bot_api.get_message_content(event.message.id)
        with open(path, 'wb') as fd:
            for chunk in audio_content.iter_content():
                fd.write(chunk)        
        fd.close()
        
        #轉檔
        AudioSegment.converter = './ffmpeg/bin/ffmpeg'
        sound = AudioSegment.from_file_using_temporary_files(path)
        path = os.path.splitext(path)[0]+'.wav'
        sound.export(path, format="wav")
        
        #辨識
        r = sr.Recognizer()
        with sr.AudioFile(path) as source:
            audio = r.record(source)
        text = r.recognize_google(audio,language='zh-Hant')

        #回傳訊息給使用者
        if text:
            event.message.text=text
            is_record = False
            message = TemplateSendMessage(
                alt_text = "醫囑紀錄",
                template = ConfirmTemplate(
                    text = '以下是我聽到的內容\n「'+text+'」\n請問內容是否需再手動編輯？',
                    actions = [
                        MessageTemplateAction(label='是，我需要手動編輯', text='重新編輯醫囑紀錄'),
                        # PostbackTemplateAction( label='是，我需要手動編輯', data='action=rerecord'),
                        PostbackTemplateAction( label='否，不需要手動編輯', data='action=norercord')
                    ]
                )
            )
            
            var_json["is_record"] = is_record
            var_json["is_entering"] = is_entering
            print(var_json)
            json_object = json.dumps(var_json, indent=2)
            with open("variables.json", "w") as outfile:
                outfile.write(json_object)
        else:
            message = TextSendMessage(text="音檔內容有誤，請重新紀錄")
    except:
        message = TextSendMessage(text="錄製過程出現錯誤，請重新紀錄")
    line_bot_api.reply_message(event.reply_token, message)
    


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    txt = event.message.text
    is_record = False
    is_entering = var_json["is_entering"]
    if is_entering:
        is_entering = False
        message = TemplateSendMessage(
            alt_text = "醫囑紀錄",
            template = ConfirmTemplate(
                text = '以下是醫囑內容\n「'+txt+'」\n是否紀錄在今天的醫囑？',
                actions = [
                    MessageTemplateAction(label='是', text='是，紀錄在今天的醫囑'),
                    MessageTemplateAction(label='否', text='否' )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif txt == "對話小百科":
        message = TemplateSendMessage( alt_text='轉盤樣板',
            template=CarouselTemplate(
                columns=[
                    CarouselColumn(
                        title='飲食健康指南',
                        text='挑選適合的飲食，改善症狀，提升生活品質。',
                        actions=[MessageTemplateAction(label=t, text=t) for t in list(comm_json.keys())[0:3]]
                    ),
                    CarouselColumn(
                        title='洞悉胃食道逆流',
                        text='深入了解胃食道逆流的不同層面',
                        actions=[MessageTemplateAction(label=t, text=t) for t in list(comm_json.keys())[3:6]]
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif txt in list(comm_json.keys()):
        print(comm_json[txt])
        for para in comm_json[txt]:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text=para.replace('\\n', '\n\n')))
    elif txt == "醫囑紀錄" or txt == "重新編輯醫囑紀錄":
        message = TemplateSendMessage(
            alt_text = "醫囑紀錄",
            template = ButtonsTemplate(
                title = '醫囑紀錄',
                text = '請問您要用什麼方式紀錄？',
                actions = [MessageTemplateAction(label='語音', text='語音'), MessageTemplateAction(label='文字', text='文字' )]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif txt == "語音":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請開始錄音'))
        is_record = True
    elif txt == "是，我需要手動編輯" or txt == "文字":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='現在起您可以開始編輯文字'))
        is_entering = True
    elif txt == "是，紀錄在今天的醫囑":
        current_time = datetime.datetime.now()
        date = str(current_time.year) + '.' + str(current_time.month) + '.' + str(current_time.day) + ' ' + str(current_time.hour) + ':' + str(current_time.minute)

        line_bot_api.reply_message(event.reply_token,TextSendMessage(text="好的，已經幫您紀錄於本日醫囑\n"+date))
    elif txt == "否，不需要手動編輯":
        message = TemplateSendMessage(
            alt_text = "醫囑紀錄",
            template = ConfirmTemplate(
                text = '是否紀錄在今天的醫囑？',
                actions = [
                    MessageTemplateAction(label='是', text='是，紀錄在今天的醫囑'),
                    MessageTemplateAction(label='否', text='否' )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif txt == "病友分享":
        ks = list(people_json.keys())
        vs = [people_json[k] for k in ks]
        print(ks, vs)
        message = TemplateSendMessage( alt_text='病友分享',
            template=CarouselTemplate(
                columns=[
                    CarouselColumn(
                        title='病友分享',
                        text='查看其他病友怎麼克服困難，改善症狀的',
                        actions=[MessageTemplateAction(label=t, text=t) for t in list(people_json.keys())[0:3]]
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif txt in list(people_json.keys()):
        strn = '\n'.join(people_json[txt])
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=strn))
    elif txt == '營養諮詢':
        message = TemplateSendMessage( alt_text='轉盤樣板',
            template=CarouselTemplate(
                columns=[
                    CarouselColumn(
                        title='李婉萍營養師',
                        text='#可預約一~五 8:00-9:00',
                        thumbnail_image_url='https://i.imgur.com/Qid7CNt.png',
                        actions=[PostbackTemplateAction( label='立即預約', data='action=reserve')]
                    ),
                    CarouselColumn(
                        title='余朱青營養師',
                        text='#可預約一~五 8:00-9:00',
                        thumbnail_image_url='https://i.imgur.com/TgEqNgG.jpg',
                        actions=[PostbackTemplateAction( label='立即預約', data='action=reserve')]
                    ),
                    CarouselColumn(
                        title='郭環棻營養師',
                        text='#可預約一~五 8:00-9:00',
                        thumbnail_image_url='https://i.imgur.com/GZYD7Yh.jpg',
                        actions=[PostbackTemplateAction( label='立即預約', data='action=reserve')]
                    ),
                    CarouselColumn(
                        title='曾依田營養師',
                        text='#可預約一~五 8:00-9:00',
                        thumbnail_image_url='https://i.imgur.com/OXe5KQy.jpg',
                        actions=[PostbackTemplateAction( label='立即預約', data='action=reserve')]
                    ),
                    CarouselColumn(
                        title='嫚嫚營養師',
                        text='#可預約一~五 8:00-9:00',
                        thumbnail_image_url='https://i.imgur.com/KRy2sG7.jpg',
                        actions=[PostbackTemplateAction( label='立即預約', data='action=reserve')]
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)

    else:
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=txt))
    
    var_json["is_record"] = is_record
    var_json["is_entering"] = is_entering
    print(var_json)
    json_object = json.dumps(var_json, indent=2)
    with open("variables.json", "w") as outfile:
        outfile.write(json_object)

@handler.add(PostbackEvent) #PostbackTemplateAction觸發此事件
def handle_postback(event):
    backdata = dict(parse_qsl(event.postback.data)) #取得Postback資料
    if backdata.get('action') == 'reserve':
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text='預約成功'))
    # elif backdata.get('action') == "rerecord":
    #     line_bot_api.reply_message(event.reply_token, TextSendMessage(text='重新編輯醫囑紀錄'))
    elif backdata.get('action') == "norecord":
        message = TemplateSendMessage(
            alt_text = "醫囑紀錄",
            template = ConfirmTemplate(
                text = '是否紀錄在今天的醫囑？',
                actions = [
                    MessageTemplateAction(label='是', text='是，紀錄在今天的醫囑'),
                    MessageTemplateAction(label='否', text='否' )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     mtext = event.message.text
#     if mtext:
#         print(mtext)
#     else:
#         print("?????????????")
 

if __name__ == '__main__':
    app.run()
