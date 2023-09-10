import abc
import redis
#
from pyinjective.async_client import AsyncClient
from pyinjective.constant import Network
#
from google.protobuf.json_format import MessageToDict
#
from utils import outils
from redis_utils import hasher
from configs.markets.injective import spot_confs as inj_spot_markets
from configs.markets.injective import derivative_confs as inj_derivative_markets

INDEX = 0

class AbstractInjectiveCacher(abc.ABC):
    _redis: redis.Redis
    def __init__(self, redis_cli: redis.Redis) -> None:
        self._redis = redis_cli
        
    async def run(self) -> None:
        while True:
            try:
                await self._starter()
                network = Network.mainnet()
                client = AsyncClient(network, insecure=False)
                await self._run_stream(client)
            except Exception as ex:
                print(ex)
                print(outils.colorize_text("Dropped.", 'red'), "Trying again.")
        
    @abc.abstractmethod
    async def _run_stream(self, client) -> None:
        pass

    @abc.abstractmethod
    async def _starter(self) -> None:
        pass

    @abc.abstractmethod
    def _get_redis_hash_key(self) -> str:
        pass

    def _save_redis(self, key: str, data: dict={}) -> None:
        if data:
            self._redis.hmset(key, data)


class AbstractPrivateInjectiveCacher(AbstractInjectiveCacher):
    _sub_id: str
    def __init__(self, subaccount_id: str, redis_cli: redis.Redis) -> None:
        super().__init__(redis_cli)
        self._sub_id = subaccount_id


class PositionCacher(AbstractPrivateInjectiveCacher):
    _market: str
    _market_id: str
    _base_decimals: str
    _quote_decimals: str
    def __init__(self, subaccount_id: str, market: str, 
                 redis_cli: redis.Redis) -> None:
        super().__init__(subaccount_id, redis_cli)
        self._market_id = inj_derivative_markets[market]["market_id"]
        self._base_decimals = inj_derivative_markets[market]["base_decimals"]
        self._quote_decimals = inj_derivative_markets[market]["quote_decimals"]
    
    async def _run_stream(self, client) -> None:
        subaccount = await client.stream_derivative_positions(
                market_id=self._market_id,
                subaccount_id=self._sub_id
            )
        async for msg in subaccount:
            self._extract_and_save(msg.position)
    
    async def _starter(self) -> None:
        network = Network.mainnet()
        client = AsyncClient(network, insecure=False)
        positions = await client.get_derivative_positions(
            market_id=self._market_id,
            subaccount_id=self._sub_id
        )
        pos_checked = False
        for position in positions.positions:
            self._extract_and_save(position)
            pos_checked = True
        if not pos_checked:
            self._save_empty()

    def _extract_and_save(self, position) -> None:
        quantity = float(position.quantity)
        print(outils.colorize_text("Position", "purple"))
        print("\t", outils.colorize_text("Quantity", "yellow"), quantity)
        if quantity == 0:
            self._save_empty()
            return
        data = {
            'quantity' : quantity * 10**(-self._base_decimals),
            'direction' : position.direction,
            'price' : float(position.entry_price) * 10**(self._base_decimals - self._quote_decimals)
        }
        print("\t", outils.colorize_text("Direction", "yellow"), data['direction'])
        print("\t", outils.colorize_text("Price", "yellow"), data['price'])
        print()
        self._save_redis(self._get_redis_hash_key(), data)

    def _get_redis_hash_key(self) -> str:
        return hasher.injective_position_hash(self._market_id)

    def _save_empty(self):
        self._save_redis(
            self._get_redis_hash_key(),
            {
                'quantity': 0,
                'direction': 'long',
                'price': 1000
            }
        )
    

class PortfolioCacher(AbstractPrivateInjectiveCacher):
    _address: str
    _denom: str
    _base_decimals: int
    def __init__(self, account_address: str, market: str, redis_cli: redis.Redis) -> None:
        super().__init__("", redis_cli)
        self._address = account_address
        self._denom = inj_spot_markets[market]["base_denom"]
        self._base_decimals = inj_spot_markets[market]["base_decimals"]

    async def _run_stream(self, client: AsyncClient) -> None:
        portfolio = await client.stream_account_portfolio(self._address)
        async for msg in portfolio:
            self._stream_extrace_and_save(MessageToDict(msg))

    async def _starter(self) -> None:
        network = Network.mainnet()
        client = AsyncClient(network, insecure=False)
        portfolio = await client.get_account_portfolio(
            self._address
        )
        self._extract_and_save(MessageToDict(portfolio))

    def _extract_and_save(self, msg) -> None:
        if 'portfolio' not in msg:
            return
        bank_balances = msg['portfolio']['bankBalances']
        if not bank_balances:
            return
        denom_filtered_bank_balances = [bb for bb in bank_balances if bb['denom'] == self._denom]
        if not denom_filtered_bank_balances:
            return
        amount = float(denom_filtered_bank_balances[0]['amount']) * 10**(-self._base_decimals)

        print(outils.colorize_text("Portfolio", 'purple'))
        print("\t", outils.colorize_text("Amount:", 'yellow'), amount)
        print()
        data = {'amount': amount}            
        self._save_redis(self._get_redis_hash_key(), data)

    def _stream_extrace_and_save(self, msg) -> None:
        if msg['type'] != "bank":
            return
        if msg['denom'] != self._denom:
            return
        amount = float(msg['amount']) * 10**(-self._base_decimals)
        print(outils.colorize_text("Portfolio", 'purple'))
        print("\t", outils.colorize_text("Amount:", 'yellow'), amount)
        print()
        data = {'amount': amount}            
        self._save_redis(self._get_redis_hash_key(), data)

    def _get_redis_hash_key(self) -> str:
        return hasher.injective_portfolio_hash(self._denom)


class DerivativeOrderbookCacher(AbstractInjectiveCacher):
    _market_id: str
    _base_decimals: int
    _quote_decimals: int
    def __init__(self, market: str, redis_cli: redis.Redis) -> None:
        super().__init__(redis_cli)
        self._market_id = inj_derivative_markets[market]["market_id"]
        self._base_decimals = inj_derivative_markets[market]["base_decimals"]
        self._quote_decimals = inj_derivative_markets[market]["quote_decimals"]

    async def _run_stream(self, client: AsyncClient) -> None:
        markets = await client.stream_derivative_orderbook(market_id=self._market_id)
        async for market in markets:
            orderbook = MessageToDict(market)['orderbook']
            self._extract_and_save(orderbook)
    
    async def _starter(self) -> None:
        network = Network.mainnet()
        client = AsyncClient(network, insecure=False)
        o = await client.get_derivative_orderbook(market_id=self._market_id)
        orderbook = MessageToDict(o.orderbook)
        self._extract_and_save(orderbook)

    def _extract_and_save(self, orderbook) -> None:
        data = {
            "highest_buyer": float(orderbook.get("buys")[0 + INDEX]['price']) * 10**(self._base_decimals - self._quote_decimals),
            "lowest_seller": float(orderbook.get("sells")[0 + INDEX]['price']) * 10**(self._base_decimals - self._quote_decimals),
            "second_highest_buyer": float(orderbook.get("buys")[1 + INDEX]['price']) * 10**(self._base_decimals - self._quote_decimals),
            "second_lowest_seller": float(orderbook.get("sells")[1 + INDEX]['price']) * 10**(self._base_decimals - self._quote_decimals),
            "highest_buy_volume": float(orderbook.get("buys")[0 + INDEX]['quantity']) * 10**(-self._base_decimals),
            "lowest_sell_volume": float(orderbook.get("sells")[0 + INDEX]['quantity']) * 10**(-self._base_decimals),
            "buys_total_volume": sum([float(ob['quantity']) for ob in orderbook['buys']]) * 10**(-self._base_decimals),
            "sells_total_volume": sum([float(ob['quantity']) for ob in orderbook['sells']]) * 10**(-self._base_decimals)
        }
        print(outils.colorize_text("Orderbook", 'purple'))
        print("\t", outils.colorize_text("Highest Buyer", 'red'), data['highest_buyer'])
        print("\t", outils.colorize_text("Highest Buy Volume", 'red'), data['highest_buy_volume'])
        print("\t", outils.colorize_text("Lowest Seller", 'red'), data['lowest_seller'])
        print("\t", outils.colorize_text("Lowest Sell Volume", 'red'), data['lowest_sell_volume'])
        print()
        self._save_redis(self._get_redis_hash_key(), data)

    def _get_redis_hash_key(self) -> str:
        return hasher.injective_derivative_orderbook_hash(self._market_id)


class DerivativeOrderHistoryCacher(AbstractPrivateInjectiveCacher):
    _market_id: str
    _base_decimals: int
    _quote_decimals: int
    def __init__(self, subaccount_id: str, market: str, 
                 redis_cli: redis.Redis) -> None:
        super().__init__(subaccount_id, redis_cli)
        self._market_id = inj_derivative_markets[market]["market_id"]
        self._base_decimals = inj_derivative_markets[market]["base_decimals"]
        self._quote_decimals = inj_derivative_markets[market]["quote_decimals"]

    async def _run_stream(self, client: AsyncClient) -> None:
        subaccount = await client.stream_historical_derivative_orders(
            market_id=self._market_id,
            subaccount_id=self._sub_id,
        )
        async for msg in subaccount:
            self._extract_and_save(MessageToDict(msg)['order'])

    async def _starter(self) -> None:
        network = Network.mainnet()
        client = AsyncClient(network, insecure=False)
        orders = await client.get_historical_derivative_orders(
            market_id=self._market_id,
            subaccount_id=self._sub_id,
            limit=5
        )
        for order in orders.orders:
            order_msg = MessageToDict(order)
            if order_msg['state'] == 'booked':
                self._extract_and_save(order_msg)

    def _extract_and_save(self, msg) -> None:
        key = msg['orderHash']
        value = {
            "state": msg['state'],
            "direction": msg['direction'],
            "filledQuantity": float(msg['filledQuantity']) * 10**(-self._base_decimals)
        }
        print(outils.colorize_text("Order", 'purple'), key)
        print("\t", outils.colorize_text("State", 'red'), value['state'])
        print("\t", outils.colorize_text("Direction", 'red'), value['direction'])
        print("\t", outils.colorize_text("Filled Quantity", 'red'), value['filledQuantity'])
        print()
        self._save_redis({'key': key, 'value': value})

    def _save_redis(self, data: dict = {}) -> None:
        self._redis.hmset(data['key'], data['value'])
        self._redis.expire(data['key'], 1200)

    def _get_redis_hash_key(self) -> str:
        pass


class SpotOrderbookCacher(DerivativeOrderbookCacher):
    def __init__(self, market: str, redis_cli: redis.Redis) -> None:
        super(AbstractInjectiveCacher, self).__init__(redis_cli)
        self._market_id = inj_spot_markets[market]["market_id"]
        self._base_decimals = inj_spot_markets[market]["base_decimals"]
        self._quote_decimals = inj_spot_markets[market]["quote_decimals"]
        
    async def _run_stream(self, client: AsyncClient) -> None:
        markets = await client.stream_spot_orderbook(market_id=self._market_id)
        async for market in markets:
            orderbook = MessageToDict(market)['orderbook']
            self._extract_and_save(orderbook)
    
    async def _starter(self) -> None:
        network = Network.mainnet()
        client = AsyncClient(network, insecure=False)
        o = await client.get_spot_orderbook(market_id=self._market_id)
        orderbook = MessageToDict(o.orderbook)
        self._extract_and_save(orderbook)
    
    def _get_redis_hash_key(self) -> str:
        return hasher.injective_spot_orderbook_hash(self._market_id)


class SpotOrderHistoryCacher(DerivativeOrderHistoryCacher):
    def __init__(self, subaccount_id: str, market: str, 
                 redis_cli: redis.Redis) -> None:
        super(AbstractPrivateInjectiveCacher, self).__init__(subaccount_id, redis_cli)
        self._market_id = inj_spot_markets[market]["market_id"]
        self._base_decimals = inj_spot_markets[market]["base_decimals"]
        self._quote_decimals = inj_spot_markets[market]["quote_decimals"]

    async def _run_stream(self, client: AsyncClient) -> None:
        subaccount = await client.stream_historical_spot_orders(
            market_id=self._market_id,
            subaccount_id=self._sub_id,
        )
        async for msg in subaccount:
            self._extract_and_save(MessageToDict(msg)['order'])

    async def _starter(self) -> None:
        network = Network.mainnet()
        client = AsyncClient(network, insecure=False)
        orders = await client.get_historical_spot_orders(
            market_id=self._market_id,
            subaccount_id=self._sub_id,
            limit=5
        )
        for order in orders.orders:
            order_msg = MessageToDict(order)
            if order_msg['state'] == 'booked':
                self._extract_and_save(order_msg)