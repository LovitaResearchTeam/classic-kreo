import redis
import asyncio
#
from stuf.safe_import import safe_import
with safe_import():
    import utils.outils as outils
    from binance_utils.cachers import FuturesSymbolSocketCacher
    import configs.redis as redis_confs
    from utils.outils import prompt_sys_for_args
#

async def main(host: str, port: int, db: int, market: str):
    redis_cli = redis.Redis(host=host, port=port, db=db)
    cacher = FuturesSymbolSocketCacher(
        market+"USDT",
        redis_cli
    )
    await cacher.start()


if __name__ == "__main__":
    outils.clear_console()
    sys_args = prompt_sys_for_args()
    market = sys_args[1]
    host = redis_confs.HOST
    port = redis_confs.PORT
    db = redis_confs.DBS['primary']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f"Running Binance on port {port} and db {db}.")
    loop.run_until_complete(main(host, port, db, market))
