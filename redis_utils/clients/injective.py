import redis
from time import sleep
from redis_utils import hasher


class PositionRedisClient:
    _redis: redis.Redis
    _market_id: str
    def __init__(self, market_id: str, redis_cli: redis.Redis) -> None:
        self._market_id = market_id
        self._redis = redis_cli
    
    def get_quantity(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), 'quantity'))

    def get_direction(self) -> float:
        return self._redis.hget(self._get_redis_hash_key(), 'direction')
    
    def get_price(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), 'price'))

    def get_all(self) -> dict:
        keys = ['quantity', 'direction', 'price']
        values = self._redis.hmget(self._get_redis_hash_key(), keys)
        while None in values:
            sleep(0.1)
            values = self._redis.hmget(self._get_redis_hash_key(), keys)
        return {
            'quantity': float(values[0]),
            'direction': values[1],
            'price': float(values[2])
        }
    
    def get_position_quantity(self):
        all_info = self.get_all()
        quantity = all_info['quantity']
        direction = all_info['direction']
        if quantity <= 0:
            return 0, 0
        if direction == b'long':
            return 0, quantity
        return quantity, 0
    
    def _get_redis_hash_key(self) -> str:
        return hasher.injective_position_hash(self._market_id)


class BalanceRedisClient:
    _denom: str
    _redis: redis.Redis
    def __init__(self, denom: str, redis_cli: redis.Redis) -> None:
        self._denom = denom
        self._redis = redis_cli

    def get_total_balance(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "total_balance"))
    
    def get_available_balance(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "available_balance"))
    
    def _get_redis_hash_key(self) -> str:
        return hasher.injective_balance_hash(self._denom)
    

class PortfolioRedisClient:
    _denom: str
    _redis: redis.Redis
    def __init__(self, denom: str, redis_cli: redis.Redis) -> None:
        self._denom = denom
        self._redis = redis_cli

    def get_amount(self) -> float:
        amount = self._redis.hget(self._get_redis_hash_key(), "amount")
        return float(amount) if amount is not None else 0
    
    def _get_redis_hash_key(self) -> str:
        return hasher.injective_portfolio_hash(self._denom)
        

class DerivativeOrderbookRedisClient:
    _redis: redis.Redis
    _market_id: str
    def __init__(self, market_id: str, redis_cli: redis.Redis) -> None:
        self._market_id = market_id
        self._redis = redis_cli

    def get_highest_buyer(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "highest_buyer"))
    
    def get_highest_buy_volume(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "highest_buy_volume"))

    def get_lowest_seller(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "lowest_seller"))
    
    def get_lowest_sell_volume(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "lowest_sell_volume"))

    def get_second_highest_buyer(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "second_highest_buyer"))
    
    def get_second_lowest_seller(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "second_lowest_seller"))

    def get_buys_total_volume(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "buys_total_volume"))

    def get_sells_total_volume(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), "sells_total_volume"))
    
    def get_highest_buy_total(self) -> float:
        keys = ['highest_buyer', 'highest_buy_volume']
        info = self._redis.hmget(self._get_redis_hash_key(), keys)
        return float(info[0]) * float(info[1])
    
    def get_lowest_sell_total(self) -> float:
        keys = ['lowest_seller', 'lowest_sell_volume']
        info = self._redis.hmget(self._get_redis_hash_key(), keys)
        return float(info[0]) * float(info[1])

    def get_both_total_volume(self) -> float:
        keys = ['buys_total_volume', 'sells_total_volume']
        info = self._redis.hmget(self._get_redis_hash_key(), keys)
        return float(info[0]), float(info[1])

    def get_highest_buyer_and_lowest_seller(self):
        keys = ["highest_buyer", "lowest_seller"]
        info = self._redis.hmget(self._get_redis_hash_key(), keys)
        return float(info[0]), float(info[1])

    def spread_market_volume_condition(self, thresh: float) -> bool:
        buys_total_volume, sells_total_volume = self.get_both_total_volume()
        if buys_total_volume <= thresh:
            return False
        return sells_total_volume > thresh

    def spread_market_price_condition(self, thresh: float) -> bool:
        buy, sell = self.get_highest_buyer_and_lowest_seller()
        percentage = (sell / buy - 1) * 100
        return percentage >= thresh

    def spread_market_condition(self, volume_threshold: float, price_threshold: float) -> bool:
        if not self.spread_market_volume_condition(volume_threshold):
            return False
        return self.spread_market_price_condition(price_threshold)

    def top_price_diff_condition(self, price: float, diff: float) -> bool:
        # diff = epsilon * factor
        return price  - self.get_highest_buyer() > diff
    
    def bottom_price_diff_condition(self, price: float, diff: float) -> bool:
        # diff = epsilon * factor
        return self.get_lowest_seller() - price > diff

    def _get_redis_hash_key(self) -> str:
        return hasher.injective_derivative_orderbook_hash(self._market_id)


class SpotOrderbookRedisClient(DerivativeOrderbookRedisClient):
    def _get_redis_hash_key(self) -> str:
        return hasher.injective_spot_orderbook_hash(self._market_id)


class OrderHistoryRedisClient:
    _redis: redis.Redis
    def __init__(self, redis_cli: redis.Redis, ) -> None:
        self._redis = redis_cli

    def get_state(self, order_hash: str) -> str:
        return self._redis.hget((order_hash).encode(), "state").decode()

    def get_direction(self, order_hash: str) -> str:
        return self._redis.hget((order_hash).encode(), "direction").decode()

    def get_filled_quantity(self, order_hash: str) -> float:
        q = self._redis.hget((order_hash).encode(), "filledQuantity")
        while q is None:
            sleep(0.5)
            q = self._redis.hget((order_hash).encode(), "filledQuantity")
        return float(q)

    def is_filled(self, order_hash: str) -> bool:
        return self.get_state(order_hash) == "filled"

    def is_canceled(self, order_hash: str) -> bool:
        return self.get_state(order_hash) == "canceled"

    def is_booked(self, order_hash: str) -> bool:
        return self.get_state(order_hash) == "booked"
    
    def get_open_order_hashes(self):
        keys = self._redis.keys("*")
        order_hashes = [k.decode() for k in keys]
        open_order_hashes = [k for k in order_hashes if self.is_booked(k)]
        return open_order_hashes
