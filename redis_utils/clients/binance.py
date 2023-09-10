import redis
from redis_utils import hasher


class AssetRedisClient:
    _redis: redis.Redis
    def __init__(self, redis_cli: redis.Redis) -> None:
        self._redis = redis_cli

    def get_asset_balance(self, asset) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), asset))
    
    def _get_redis_hash_key(self) -> str:
        return hasher.binance_asset_hash()
    

class SpotSymbolClient:
    _redis: redis.Redis
    _symbol: str
    def __init__(self, symbol: str, redis_cli: redis.Redis) -> None:
        self._redis = redis_cli
        self._symbol = symbol
    
    def get_bid(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), 'bid'))
    
    def get_ask(self) -> float:
        return float(self._redis.hget(self._get_redis_hash_key(), 'ask'))
    
    def get_ask_bid(self) -> list[float]:
        return [float(p) for p in self._redis.hmget(self._get_redis_hash_key(), ["ask", "bid"])]
    
    def _get_redis_hash_key(self) -> str:
        return hasher.binance_spot_symbol_hash(self._symbol)


class FuturesSymbolClient(SpotSymbolClient):
    def _get_redis_hash_key(self) -> str:
        return hasher.binance_futures_symbol_hash(self._symbol)