"""
    python scripts/inj_balance_cacher.py <wallet-number> <market>
"""
import redis
import asyncio
#
from stuf.safe_import import safe_import
with safe_import():
    import utils.outils as outils
    from injective_utils.cachers import PortfolioCacher
    import configs.redis as redis_confs
    from settings.credentials.injective import WALLETS
#

async def main(host: str, port: int, db: int, market: str, address: str):
    redis_cli = redis.Redis(host=host, port=port, db=db)
    cacher = PortfolioCacher(address, market, redis_cli)
    await cacher.run()


if __name__ == "__main__":
    outils.clear_console()
    host = redis_confs.HOST
    port = redis_confs.PORT
    sys_args = outils.prompt_sys_for_args()
    wallet_number = int(sys_args[1])
    market = sys_args[2]
    address = WALLETS[wallet_number]["address"]
    db = redis_confs.DBS['primary']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f"Running Position Cacher on port {port} and db {db}.")
    loop.run_until_complete(main(host, port, db, market, address))
