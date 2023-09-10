import requests
import urllib
from os import system
import sys
from math import ceil, floor


def cal_diff_percentage(p1: float, p2: float) -> float:
    return (p1/p2 - 1) * 100


def cal_total_percentage(amount: float, total: float) -> float:
    return amount / total * 100


def clear_console():
    system("clear")


def prompt_user_for_market(markets=["ETH", "BTC"]):
    market = input(
        f"ENTER MARKET NAME IN CAPITAL ({', '.join(markets)}) (DEFAULT: {markets[0]}, ): "
    )
    if market.strip() == "":
        market = markets[0]
    return market


def prompt_sys_for_args():
    markets = sys.argv[:]
    return markets


def colorize_text(text, color):
    colors = {
        'red': "\u001b[31m",
        'yellow': "\u001b[33m",
        'blue': '\u001b[34m',
        'reset': "\u001b[0m",
        'green': "\u001b[32m",
        'purple': '\u001b[35m',
        'cyan': '\u001b[36m',
        'orange': '\u001b[38;5;202m',
        'indian_red': '\u001b[38;5;131m',
        'header' : '\033[95m',
        'cyanbg': '\033[106m',
        'pinkbg':'\033[105m',
        'bluebg':'\033[104m',
        'greybg':'\033[100m',
        'redbg':'\033[101m',
        'greenbg':'\033[102m',
        'yellowbg':'\033[103m'
    }
    return f"{colors[color]}{text}{colors['reset']}"


def truncate(number: float, decimals: int=0) -> float:
    return round(floor(number * 10**(decimals)) / 10**(decimals), decimals)


def truncate_up(number: float, decimals: int=0) -> float:
    return round(ceil(number * 10**(decimals)) / 10**(decimals), decimals)


def tg_send_message(text, tg_token: str, tg_chatid: str):
    URL = 'https://api.telegram.org/bot{token}/'.format(token=tg_token)
    tot = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}".format(tot, tg_chatid)    
    r = requests.get(url)
    if not r.status_code == requests.codes.OK:
        raise Exception(colorize_text(r.content, 'pinkbg'))
    else:
        print(colorize_text("tg sent", 'pinkbg'))