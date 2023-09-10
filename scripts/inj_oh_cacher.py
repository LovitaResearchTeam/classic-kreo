"""
    python scripts/inj_oh_cacher.py <wallet-number> <market>
"""

import redis
import asyncio
#
from stuf.safe_import import safe_import
with safe_import():
    import utils.outils as outils
    from injective_utils.cachers import DerivativeOrderHistoryCacher
    import configs.redis as redis_confs
    from settings.credentials.injective import WALLETS


async def main(host: str, port: int, db: int, market: str, subaccount_id: str):
    redis_cli = redis.Redis(host=host, port=port, db=db)
    ohc = DerivativeOrderHistoryCacher(subaccount_id, market, redis_cli)
    await ohc.run()


if __name__ == "__main__":
    outils.clear_console()
    host = redis_confs.HOST
    port = redis_confs.PORT
    sys_args = outils.prompt_sys_for_args()
    wallet_number = int(sys_args[1])
    market = sys_args[2]
    subaccount_id = WALLETS[wallet_number]["subaccount_id"]
    db = redis_confs.DBS[f'injectiveOrderHistoryCacher{market}']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print(f"Running Order History Cacher on port {port} and db {db} for market {market}")
    loop.run_until_complete(main(host, port, db, market, subaccount_id))