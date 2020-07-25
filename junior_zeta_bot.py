# created using: https://www.codementor.io/garethdwyer/building-a-telegram-bot-using-python-part-1-goi5fncay

import json
import os
import time
import urllib.parse
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from dbhelper import DBHelper
import logging

# Telegram bot specific constants
SHOW_LOG_COMMAND = "/log"

CHROME_DRIVER_PATH = None

TELEGRAM_API_URL = "https://api.telegram.org/bot{}/"

TIMEOUT = 3600 * 4

db = DBHelper()

# App specific constants
WATERING_CAN_ID = 'div.f-kettle-body'

DOWNLOAD_IMG_ID = 'div.download-img'

CONFUSED_RESPONSE = "I am confused 😕"

SUCCESS_RESPONSE = "Successfully watered your plant today 🌱"

FAIL_RESPONSE = "I was not able to water your plant [[{}]] 😓 Please try again"

ERROR_RESPONSE = "Oops something went wrong... Please try again"

LIMIT = 5

logger = logging.getLogger(__name__)


def init():
    global TELEGRAM_API_URL, CHROME_DRIVER_PATH
    CHROME_DRIVER_PATH = ChromeDriverManager().install()
    TELEGRAM_API_URL = TELEGRAM_API_URL.format(os.environ.get('TOKEN'))

    db.setup()


def get_url(url):
    """
    Downloads the content from a URL and returns a string
    :param url: A URL string
    :return: A repsonse string
    """
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    """
    Gets the string response and parses it into a Python dictionary
    :param url: A URL string
    :return: A Python dictionary containing the response
    """
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    """
    Retrieves a list of "updates" (messages sent to the bot)
    :param offset:
    :return:
    """
    url = TELEGRAM_API_URL + f"getUpdates?timeout={TIMEOUT}"
    if offset:
        url += "&offset={}".format(offset)
    resp = get_json_from_url(url)
    return resp


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def get_last_chat_id_and_text(updates):
    """
    Get the chat ID and the message text of the most recent message sent to the bot
    :param updates:
    :return:
    """
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return text, chat_id


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(str(text))
    url = TELEGRAM_API_URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


def water_plant(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    count = 0
    while count < LIMIT:
        browser = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=chrome_options)
        browser.get(url)
        present = WebDriverWait(browser, 5).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, WATERING_CAN_ID)))
        if not present:
            return False, count
        watering_can = browser.find_element_by_css_selector(WATERING_CAN_ID)
        watering_can.click()
        # To check if watering was successful
        present = WebDriverWait(browser, 10).until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, DOWNLOAD_IMG_ID)))
        if not present:
            return False, count
        count += 1
        browser.quit()
    return True, count


def send_latest_log(chat_id):
    latest_log = db.get_latest_log()
    send_message(latest_log, chat_id)


def parse_message(text):
    start_idx = text.find('http')
    url = text[start_idx:len(text)]
    return url


def validate_url(url):
    result = urllib.parse.urlparse(url)
    if result.scheme != 'http' and not result.netloc:
        return False
    return True


def handle_updates(updates):
    for update in updates["result"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        if 'html' in text:
            url = parse_message(text)
            if not validate_url(url):
                send_message(CONFUSED_RESPONSE, chat_id)
                return
            try:
                has_watered, count = water_plant(url)
                reply = SUCCESS_RESPONSE if has_watered else FAIL_RESPONSE.format(count + 1)
                send_message(reply, chat_id)
            except Exception as err:
                db.add_log(datetime.now(), err)
                logger.error(err)
                send_message(ERROR_RESPONSE, chat_id)
        elif text == SHOW_LOG_COMMAND:
            send_latest_log(chat_id)
        else:
            send_message(CONFUSED_RESPONSE, chat_id)


def main():
    init()
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
