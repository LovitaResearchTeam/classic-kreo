import urllib
import requests
from utils.outils import colorize_text


class TelegramClient:
    _token: str
    _chatid: int
    def __init__(self, token: str, chatid: int) -> None:
        self._token = token
        self._chatid = chatid

    def send_message(self, text: str):
        URL = 'https://api.telegram.org/bot{token}/'.format(token=self._token)
        tot = urllib.parse.quote_plus(text)
        url = URL + "sendMessage?text={}&chat_id={}".format(tot, self._chatid)    
        r = requests.get(url)
        if not r.status_code == requests.codes.OK:
            raise Exception(colorize_text(r.content, 'pinkbg'))
        else:
            print(colorize_text("tg sent", 'pinkbg'))