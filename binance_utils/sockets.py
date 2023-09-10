import abc
import asyncio
import threading
#
from binance import AsyncClient
from binance import BinanceSocketManager
#
from settings.credentials import binance as binance_confs

#NOTE: Depricated and should be migrated

BIN_CRED = {
    "api_key": binance_confs.API_KEY,
    "api_secret": binance_confs.API_SECRET
}

class AbstractBinanceSocketClient(abc.ABC):
    def __init__(self) -> None:
        pass

    def start(self):
        th = threading.Thread(target=self._between)
        th.start()

    def _between(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._target())
        loop.close()

    async def _target(self):
        client = await AsyncClient.create(**BIN_CRED)
        socket_manager = BinanceSocketManager(client)
        ticker_socket = self.get_socket(socket_manager)
        async with ticker_socket as ts:
            while True:
                try:
                    res = await ts.recv()
                    await self._callback(res)
                except Exception as e:
                    print(e)
                    await asyncio.sleep(2)

    @abc.abstractmethod
    async def _callback(self, data):
        pass
    
    @abc.abstractmethod
    def get_socket(self, socket_manager):
        pass
    

class BinanceAssetSocket(AbstractBinanceSocketClient):
    balances: dict
    def __init__(self) -> None:
        self.balances = {}
    
    async def _callback(self, data):
        if data.get('e') == 'outboundAccountPosition':
            self.price = float(data['c'])
            for asset in data.get('B'):
                self.balances[asset.get('a')] = float(asset.get('f'))
            print("Balance change.")
        else:
            print("AJIB", data)
        print("balances: ", self.balances)

    def get_socket(self, socket_manager: BinanceSocketManager):
        return socket_manager.user_socket()


class BinancePriceSocket(AbstractBinanceSocketClient):
    _market: str
    price: float
    def __init__(self, market) -> None:
        self._market = market
        self.price = None
    
    async def _callback(self, msg):
        if msg['e'] == "24hrTicker":
            self.price = float(msg['c'])

    async def get_price(self):
        while True:
            if self.price is not None:
                return self.price
            await asyncio.sleep(2)
    
    def get_socket(self, socket_manager: BinanceSocketManager):
        return socket_manager.symbol_ticker_socket(self._market)


