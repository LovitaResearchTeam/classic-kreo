import asyncio

from injective_utils.trader import DerivativeInjectiveTrader
from utils.outils import prompt_sys_for_args
from settings.credentials.injective import WALLETS
from configs.markets.injective import derivative_confs


async def cancel(markets: list[str]):
    for i, market in enumerate(markets):
        trader = await DerivativeInjectiveTrader.create(
            WALLETS[i]['wallet_key']
        )
        await trader.batch_update(
            derivative_confs[market]['market_id'], []
        )


if __name__ == "__main__":
    print("Canceling given markets")
    markets = prompt_sys_for_args()[1:]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cancel(markets))
