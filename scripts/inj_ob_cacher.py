import redis
import asyncio
#
from stuf.safe_import import safe_import
with safe_import():
    from injective_utils.cachers import DerivativeOrderbookCacher
    import configs.redis as redis_confs
    import utils.outils as outils


async def main(host: str, port: int, db: int, market: str):
    redis_cli = redis.Redis(host=host, port=port, db=db)
    obc = DerivativeOrderbookCacher(market, redis_cli)
    await obc.run()


if __name__ == "__main__":
    outils.clear_console()
    host = redis_confs.HOST
    port = redis_confs.PORT
    sys_args = outils.prompt_sys_for_args()
    market = sys_args[1]
    db = redis_confs.DBS['primary']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f"Running Order Book Cacher on port {port} and db {db} for market {market}")
    loop.run_until_complete(main(host, port, db, market))