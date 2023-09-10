import asyncio
import time

from binance import AsyncClient
import pprint
#
from stuf.safe_import import safe_import
with safe_import():
    from utils import outils
    from injective_utils.actioners import DerivativeOrderHistorySocketActioner
    from settings.credentials.binance import API_KEY, API_SECRET
    from settings.credentials.injective import WALLETS
    from configs.markets.injective import derivative_confs
    from settings.markets import market_settings
    from settings.telegram import TOKEN, CHAT_ID
    from utils.tgcli import TelegramClient
#

class BinanceEqualMarketer:
    orders: dict
    market: str
    symbol: str
    market_id: str
    binance_trader: AsyncClient
    telegram_cli: TelegramClient
    def __init__(self, market: str, binance_trader: AsyncClient):
        self.market = market
        self.symbol = market+"USDT"
        self.market_id = derivative_confs[market]['market_id']
        self.orders = {}
        self.binance_trader = binance_trader
        self.telegram_cli = TelegramClient(TOKEN, CHAT_ID)
    
    def add_order(self, order):
        order_hash = order['orderHash']
        print("order", order_hash, "added")
        self.orders[order_hash] = {
            'filled_quantity': float(order['filledQuantity']),
            'direction': order['direction']
        }

    def remove_order(self, order):
        order_hash = order['orderHash']
        print("order", order_hash, "removed")
        if order_hash in self.orders:
            del self.orders[order_hash]
        else:
            print("WARNING: order not found in cache.")

    def get_remain_quantity(self, order):
        order_hash = order['orderHash']
        filled_quantity = float(order['filledQuantity'])
        prev = self.orders[order_hash]['filled_quantity'] if order_hash in self.orders else 0
        print(prev, "was filled but now", filled_quantity, "has been filled.")
        print("so the remaining quantity to market in binance is", filled_quantity - prev)
        return round(filled_quantity - prev, market_settings[market]['round_decis'])
    
    async def trade_in_binance(self, order):
        direction = order['direction']
        print("ORDER")
        q = self.get_remain_quantity(order)
        while True:
            try:
                return await self.binance_trader.futures_create_order(
                    symbol=self.symbol,
                    side='BUY' if direction.upper() == "SELL" else 'SELL',
                    type="MARKET",
                    timestamp=int(time.time()),
                    quantity=q
                )
            except:
                print("error in binance trade")
    
    async def booked_order_msg_handler(self, order):
        self.add_order(order)
        pprint.pprint(self.orders)

    async def canceled_order_msg_handler(self, order):
        self.remove_order(order)
        pprint.pprint(self.orders)

    async def filled_order_msg_handler(self, order):
        self.telegram_cli.send_message(
            "order \n"+ str(order) + "\n fully filled. Trying to trade in binance."
        )
        print(await self.trade_in_binance(order))
        self.remove_order(order)
        pprint.pprint(self.orders)

    async def partial_filled_order_msg_handler(self, order):
        self.telegram_cli.send_message(
            "order \n"+ str(order) + "\n partially filled. Trying to trade in binance."
        )
        print(await self.trade_in_binance(order))
        self.add_order(order)
        pprint.pprint(self.orders)

    async def handler(self, order) -> None:
        objective = self.get_handler_dict()[order['state']]
        return await objective(order)
        
    def get_handler_dict(self):
        return  {
            'booked': self.booked_order_msg_handler,
            'canceled': self.canceled_order_msg_handler,
            'filled': self.filled_order_msg_handler,
            'partial_filled': self.partial_filled_order_msg_handler
        }
    

async def main(market: str, subaccount_id: str):
    binance_trader = await AsyncClient.create(API_KEY, API_SECRET)
    equalizer = BinanceEqualMarketer(
        market,
        binance_trader,
    )
    socket_actioner = DerivativeOrderHistorySocketActioner(
        subaccount_id,
        market,
        equalizer.handler
    )
    await socket_actioner.run()


if __name__ == "__main__":
    print("HI")
    print("-"*40)
    sys_args = outils.prompt_sys_for_args()
    wallet_number = int(sys_args[1])
    market = sys_args[2]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    subaccount_id = WALLETS[wallet_number]["subaccount_id"]
    loop.run_until_complete(main(market, subaccount_id))