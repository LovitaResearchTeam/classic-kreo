import abc
import asyncio
import redis
#
from binance import AsyncClient
from binance import BinanceSocketManager
#
from utils.outils import colorize_text
from utils.tgcli import TelegramClient
from settings.credentials import binance as binance_confs
from settings.telegram import TOKEN, CHAT_ID
from redis_utils import hasher

BIN_CRED = {
    "api_key": binance_confs.API_KEY,
    "api_secret": binance_confs.API_SECRET
}

class AbstractBinanceSocketCacher(abc.ABC):
    _redis: redis.Redis
    _timeout: int
    _tg_cli: TelegramClient
    def __init__(self, redis_cli: redis.Redis, timeout:int) -> None:
        self._redis = redis_cli
        self._timeout = timeout
        self._tg_cli = TelegramClient(
            TOKEN, CHAT_ID
        )

    async def start(self):
        while True:
            await self._target()

    async def _target(self):
        await self._starter()
        client = await AsyncClient.create(**BIN_CRED)
        socket_manager = BinanceSocketManager(client)
        ticker_socket = self._get_socket(socket_manager)
        async with ticker_socket as ts:
            while True:
                try:
                    res = await asyncio.wait_for(ts.recv(), timeout=self._timeout)
                    await self._callback(res)
                except asyncio.TimeoutError:
                    await self._handle_timeout()
                    return
                except Exception as e:
                    print(e)
                    await asyncio.sleep(2)

    @abc.abstractmethod
    async def _callback(self, data) -> None:
        pass
    
    @abc.abstractmethod
    async def _starter(self) -> None:
        pass

    @abc.abstractmethod
    def _save_redis_all(self, data:dict={}) -> None:
        pass
    
    @abc.abstractmethod
    def _get_socket(socket_manager):
        pass

    @abc.abstractmethod
    async def _handle_timeout():
        pass

    @abc.abstractmethod
    def _print_data(self, data: dict) -> None:
        pass


class AssetSocketCacher(AbstractBinanceSocketCacher):
    balances: dict
    def __init__(self, redis_cli: redis.Redis, timeout: int = 3600) -> None:
        super().__init__(redis_cli, timeout)

    async def _callback(self, data):
        if data.get('e') == 'outboundAccountPosition':
            B = data['B']
            balances = {}
            for asset in B:
                balances[asset['a']] = float(asset['f'])
            self._save_redis_all(balances)
            self._print_data(balances)
        
    def _get_socket(self, socket_manager: BinanceSocketManager):
        return socket_manager.user_socket()
    
    async def _starter(self):
        client = await AsyncClient.create(**BIN_CRED)
        result = await client.get_account()
        balances = {}
        for a in result['balances']:
            asset = a['asset']
            free = float(a['free'])
            if free > 0:
                balances[asset] = free
        self._save_redis_all(balances)
        self._print_data(balances)
    
    def _save_redis_all(self, data: dict={}) -> None:
        if data:
            self._redis.hmset(self._get_redis_hash_key(), data)

    def _get_redis_hash_key(self) -> str:
        return hasher.binance_asset_hash()
    
    def _print_data(self, data: dict) -> None:
        print(colorize_text("Binance Asset Balances: ", 'purple'))
        for a, f in data.items():
            print(f"\t{colorize_text(a, 'green')}: {f}")
        print()

    async def _handle_timeout(self):
        message = "Binance Asset Websocket timeout reached. Trying to starting again."
        print(colorize_text(message, "red"))
        self._tg_cli.send_message(message)


class SpotSymbolSocketCacher(AbstractBinanceSocketCacher):
    _symbol: str
    def __init__(self, symbol: str, redis_cli: redis.Redis, timeout:int = 5) -> None:
        super().__init__(redis_cli, timeout)
        self._symbol = symbol

    async def _callback(self, data):
        if data['e'] == "24hrTicker":
            out = {
                'bid': float(data['b']),
                'ask': float(data['a'])
            }
            self._save_redis_all(out)
            self._print_data(out)

    def _get_socket(self, socket_manager: BinanceSocketManager):
        return socket_manager.symbol_ticker_socket(self._symbol)
    
    async def _starter(self):
        pass

    def _save_redis_all(self, data: dict={}) -> None:
        if data:
            self._redis.hmset(self._get_redis_hash_key(), data)

    def _print_data(self, data: dict) -> None:
        print(colorize_text(f"Binance {self._symbol} ticker socket cacher:", 'yellow'))
        print("\t", colorize_text("bid =", 'blue'), data['bid'])
        print("\t", colorize_text("ask =", 'blue'), data['ask'])
        print()

    async def update_with_api(self):
        client = await AsyncClient.create()
        ob = await client.get_order_book(symbol=self._symbol)
        ask = ob['asks'][0]
        bid = ob['bids'][0]
        out = {
            'bid': bid,
            'ask': ask
        }
        self._save_redis_all(out)
        print("from api")
        self._print_data(out)


    async def _handle_timeout(self):
        await self.update_with_api()
        m = u"🔴🔴🔴🔴🔴"+"Binance BidAsk Websocket timeout reached."
        self._tg_cli.send_message(m)
        print(colorize_text(m, "red"))

    def _get_redis_hash_key(self) -> str:
        return hasher.binance_spot_symbol_hash(self._symbol)
   

class FuturesSymbolSocketCacher(SpotSymbolSocketCacher):
    def __init__(self, symbol: str, redis_cli: redis.Redis, timeout: int = 2) -> None:
        super().__init__(symbol, redis_cli, timeout)

    async def _callback(self, data):
        if data['data']['e'] == "bookTicker":
            out = {
                'bid': float(data['data']['b']),
                'ask': float(data['data']['a'])
            }
            self._save_redis_all(out)
            self._print_data(out)

    def _get_socket(self, socket_manager: BinanceSocketManager):
        return socket_manager.symbol_ticker_futures_socket(self._symbol)
    
    async def _starter(self):
        pass

    async def update_with_api(self):
        client = await AsyncClient.create()
        ob = await client.futures_order_book(symbol=self._symbol)
        ask = ob['asks'][0]
        bid = ob['bids'][0]
        out = {
            'bid': bid,
            'ask': ask
        }
        self._save_redis_all(out)
        print("from api")
        self._print_data(out)

    async def _handle_timeout(self):
        await self.update_with_api()
        m = u"🔴🔴🔴🔴🔴"+"Binance Futures BidAsk Websocket timeout reached."
        self._tg_cli.send_message(m)
        print(colorize_text(m, "red"))

    def _get_redis_hash_key(self) -> str:
        return hasher.binance_futures_symbol_hash(self._symbol)
