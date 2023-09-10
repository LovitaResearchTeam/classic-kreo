import abc
import redis
#
from redis_utils import hasher


class AbstractAutopilotRedisClient(abc.ABC):
    _redis: redis.Redis
    def __init__(self, redis_cli: redis.Redis) -> None:
        self._redis = redis_cli

    def get_buy_from(self):
        return float(self._redis.hget(self._get_redis_hash_key(), "buy_from"))

    def get_sell_to(self):
        return float(self._redis.hget(self._get_redis_hash_key(), "sell_to"))

    @abc.abstractmethod
    def _get_redis_hash_key(self) -> str:
        pass


class BinanceBalanceAutopilotRedisClient(AbstractAutopilotRedisClient):
    _asset: str
    def __init__(self, asset: str, redis_cli: redis.Redis) -> None:
        super().__init__(redis_cli)
        self._asset = asset
    
    def _get_redis_hash_key(self) -> str:
        return hasher.autopilot_binance_balance_hash(self._asset)
    

class InjectivePositionAutopilotRedisClient(AbstractAutopilotRedisClient):
    _asset: str
    def __init__(self, asset: str, redis_cli: redis.Redis) -> None:
        super().__init__(redis_cli)
        self._asset = asset
    
    def _get_redis_hash_key(self) -> str:
        return hasher.autopilot_injective_position_hash(self._asset)


class InjectiveBalanceAutopilotRedisClient(AbstractAutopilotRedisClient):
    _asset: str
    def __init__(self, asset: str, redis_cli: redis.Redis) -> None:
        super().__init__(redis_cli)
        self._asset = asset

    def _get_redis_hash_key(self) -> str:
        return hasher.autopilot_injective_balance_hash(self._asset)



