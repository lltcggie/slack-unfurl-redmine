import os
import threading
import requests
import urllib
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from lxml import html


MAX_DESCRIPTION_LINE_NUM = int(os.environ.get("MAX_DESCRIPTION_LINE_NUM", '5')) # チケットの詳細表示の最大行数
MAX_DESCRIPTION_LENGTH = int(os.environ.get("MAX_DESCRIPTION_LENGTH", '500'))  # チケットの詳細表示の最大文字数

API_KEY_SAVE_PATH = './data/key.json'
ADMIN_USER_ID_LIST = os.environ.get("ADMIN_USER_ID_LIST").split(';')


channel_to_redmine_api_key_map = {}
lock_channel_to_redmine_api_key_map = threading.Lock() 

api_key_save_dir = os.path.dirname(API_KEY_SAVE_PATH)
if not os.path.isdir(api_key_save_dir):
    os.makedirs(api_key_save_dir)

if os.path.isfile(API_KEY_SAVE_PATH):
    with open(API_KEY_SAVE_PATH, "r") as file:
        channel_to_redmine_api_key_map = json.load(file)

# ボットトークンと署名シークレットを使ってアプリを初期化します
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    #signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

def is_admin_user(user_id):
    return user_id in ADMIN_USER_ID_LIST

def atomic_save(path, data):
    new_path = API_KEY_SAVE_PATH + '.new'
    with open(new_path, "w") as f:
        f.write(data)
    os.replace(new_path, path)

def truncate(string, line_count, length, ellipsis='...'):
    '''文字列を切り詰める

    string: 対象の文字列
    length: 切り詰め後の長さ
    ellipsis: 省略記号
    '''
    lines = string.split('\n')
    truncated = len(lines[line_count:]) > 0
    lines = lines[:line_count]
    string_truncated = '\n'.join(lines)
    truncated = truncated or string[length:] != ''

    return string_truncated[:length] + (ellipsis if truncated else '')

def generate_blocks(url, REDMINE_API_KEY):
    filepath = urllib.parse.urlparse(url).path
    headers = {'X-Redmine-API-Key': REDMINE_API_KEY}
    urlData = requests.get(url, headers=headers).content
    tree = html.fromstring(urlData)

    title = tree.xpath('//title/text()')[0]
    icon_url = urllib.parse.urljoin(url, tree.xpath("//link[@rel='shortcut icon']/@href")[0])

    blocks = {
        "blocks": [{
			"type": "context",
			"elements": [
				{
					"type": "image",
					"image_url": icon_url,
					"alt_text": "favicon.ico"
				},
				{
					"type": "mrkdwn",
					"text": "<{}|*{}*>".format(url, title)
				}
			]
		}]
    }

    if filepath.startswith('/issues/'): # チケットだったら内容の一部も表示する
        description_elm = tree.xpath("//div[@class='description']/div[@class='wiki']/p")
        if len(description_elm) > 0:
            description = truncate(tree.xpath("//div[@class='description']/div[@class='wiki']/p")[0].text_content(),
                MAX_DESCRIPTION_LINE_NUM, MAX_DESCRIPTION_LENGTH)
            blocks["blocks"][0]["elements"].append({
                "type": "plain_text",
                "text": description,
                "emoji": True
            })

    return blocks

def generate_channle_id_to_name_map(client):
    cl = client.conversations_list(exclude_archived=False, types='public_channel,private_channel')
    if not cl.data['ok']:
        return None

    channle_id_to_name_map = {}
    for channel in cl.data['channels']:
        channel_id = channel['id']
        channel_name = channel['name']
        channle_id_to_name_map[channel_id] = channel_name

    return channle_id_to_name_map

# リンクを展開する
@app.event("link_shared")
def handle_link_shared_events(body, ack, client):
    ack()

    channel_id = body["event"]["channel"]

    api_key = None
    with lock_channel_to_redmine_api_key_map:
        if channel_id in channel_to_redmine_api_key_map:
            api_key = channel_to_redmine_api_key_map[channel_id]

    if api_key:
        unfurls = {}
        for urls in body["event"]["links"]:
            url = urls["url"]
            unfurls[url] = generate_blocks(url, api_key)

        client.chat_unfurl(
            channel = channel_id,
            ts = body["event"]["message_ts"],
            unfurls = unfurls
        )

# APIキーを登録する
@app.command("/redmine_register_api_key")
def redmine_register_api_key(ack, respond, command):
    ack()

    user_id = command['user_id']
    if not is_admin_user(user_id):
        respond(f"あなたは管理ユーザーではありません")
        return

    channel_id = command['channel_id']
    api_key = command['text']
    respond_message = ''
    with lock_channel_to_redmine_api_key_map:
        changed = False
        if len(api_key) > 0:
            channel_to_redmine_api_key_map[channel_id] = api_key
            changed = True
            respond_message = "APIキーを登録しました: {}".format(api_key)
        elif channel_id in channel_to_redmine_api_key_map:
            channel_to_redmine_api_key_map.pop(channel_id)
            changed = True
            respond_message = "APIキーを削除しました"
        else:
            respond_message = "APIキーが登録されていません"

        if changed: # 永続化する
            json_string = json.dumps(channel_to_redmine_api_key_map, indent=4)
            atomic_save(API_KEY_SAVE_PATH, json_string)

    respond(respond_message)

# 登録したAPIキーのリストを表示する
@app.command("/redmine_list_registered_api_key")
def redmine_list_registered_api_key(ack, respond, command, client):
    ack()

    user_id = command['user_id']
    if not is_admin_user(user_id):
        respond(f"あなたは管理ユーザーではありません")
        return

    channle_id_to_name_map = generate_channle_id_to_name_map(client)
    respond_text = ''
    with lock_channel_to_redmine_api_key_map:
        for channel_id, api_key in channel_to_redmine_api_key_map.items():
            if channel_id in channle_id_to_name_map:
                channel_name = channle_id_to_name_map[channel_id]
                respond_text = respond_text + '{}: {}\n'.format(channel_name, api_key)
            else: # チャンネルが削除されてたらマップからも消す
                channel_to_redmine_api_key_map.pop(channel_id)
    if len(respond_text) > 0:
        respond_text = respond_text[:-1] # 最後の改行を取り除く
        respond(respond_text)
    else:
        respond(f"APIキーが登録されていません")

# アプリを起動します
if __name__ == "__main__":
    #app.start(port=int(os.environ.get("PORT", 3000)))
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
