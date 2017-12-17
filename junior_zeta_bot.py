# created using: https://www.codementor.io/garethdwyer/building-a-telegram-bot-using-python-part-1-goi5fncay

import json
import requests
import time
import urllib
from dbhelper import DBHelper

LIST_HEADER = "Todo list:\n"

COMMAND_CHARACTER = "/"

START_COMMAND = "/start"

DONE_COMMAND = "/done"

SHOW_COMMAND = "/show"

MESSAGE_DELETE_ITEM = "Select an item to delete"

MESSAGE_EMPTY_LIST = "There is nothing on your todo list."

MESSAGE_STARTUP = "*Welcome to your personal To Do list.*\n" \
                  + "- Send any text to me and I'll store it as an item.\n"\
                  + "- Send /done to remove items \n" + "- Send /show to show all items"

TOKEN = "487892536:AAETCkb0f8Druow7YzMV_lo9WESiWUUNAiU"

URL = "https://api.telegram.org/bot{}/".format(TOKEN)

db = DBHelper()
db.setup()


# downloads the content from a URL and returns a string
def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


# gets the string response and parses it into a Python dictionary
def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json_from_url(url)
    return js


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


def handle_updates(updates):
    for update in updates["result"]:
        chat = update["message"]["chat"]["id"]
        try:
            text = update["message"]["text"]
            items = db.get_items()
            process_text(chat, text, items)
        # if user sends any kind of media instead of text
        except KeyError:
            send_message("Media is saved.", chat)


def process_text(chat, text, items):
    if text == DONE_COMMAND:
        show_items_to_delete(chat, items)
    elif text == START_COMMAND:
        send_message(MESSAGE_STARTUP, chat)
    elif text == SHOW_COMMAND:
        show_full_list(chat)
    elif text.startswith(COMMAND_CHARACTER):
        pass
    elif text in items:
        db.delete_item(text)
        items = db.get_items()
        show_items_to_delete(chat, items)
    else:
        db.add_item(text)
        show_full_list(chat)


def show_full_list(chat):
    items = db.get_items()
    if not items:
        send_message(MESSAGE_EMPTY_LIST, chat)
    else:
        message = LIST_HEADER + "\n".join(items)
        send_message(message, chat)


def show_items_to_delete(chat, items):
    if items:
        keyboard = build_keyboard(items)
        send_message(MESSAGE_DELETE_ITEM, chat, keyboard)
    else:
        send_message(MESSAGE_EMPTY_LIST, chat, remove_keyboard())


def build_keyboard(items):
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard": keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def remove_keyboard():
    reply_markup = {"remove_keyboard": True}
    return json.dumps(reply_markup)


def main():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handle_updates(updates)
        # put a small delay between requests (this is kinder to Telegram's servers and better for our own network
        # resources)
        time.sleep(0.3)


if __name__ == '__main__':
    main()
