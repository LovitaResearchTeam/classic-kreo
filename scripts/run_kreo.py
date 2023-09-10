import asyncio
import threading
import redis
from time import sleep
import pprint
#
from stuf.safe_import import safe_import
with safe_import():
    from settings.credentials.injective import WALLETS
    from configs.markets.injective import derivative_confs as inj_derivative_markets
    from configs.contrib_params import derivative_params as der_contrib_params
    from settings.other import LEVERAGE, MIN_ORDER_TETHER, FIRST_ORDER_MULTIPLIER, RISK_ORDER_TETHER, RISK_ORDER_NO
    from settings.markets import market_settings
    from configs import redis as redis_confs
    from settings.other import POST_ONLY
    from injective_utils.trader import DerivativeInjectiveTrader
    from redis_utils.clients.injective import PositionRedisClient
    from redis_utils.clients.binance import FuturesSymbolClient
    from utils import outils
#


class ConditionManager:
    check_event: threading.Event
    price_event: threading.Event
    bin_symbol_cli: FuturesSymbolClient
    buy_price: float
    sell_price: float
    def __init__(self, bin_symbol_cli: FuturesSymbolClient) -> None:
        self.check_event = threading.Event()
        self.price_event = threading.Event()
        self.bin_symbol_cli = bin_symbol_cli
        self.buy_price = None
        self.sell_price = None

    def start(self, market: str):
        self.start_bin_symbol_checker(market)

    def check(self, prices):
        print("Checking")
        self.buy_price = prices[0]
        self.sell_price = prices[1]
        self.price_event.set()
        self.check_event.clear()
        self.check_event.wait()

    def start_bin_symbol_checker(self, market: str):
        th = threading.Thread(target=self.bin_symbol_checker_target, args=(market,))
        th.start()
        
    def bin_symbol_checker_target(self, market: str):
        while self.buy_price is None:
            sleep(0.2)
        buy_upper = market_settings[market]["condition_coefs"]["buy"]["upper_edge"]
        buy_lower = market_settings[market]["condition_coefs"]["buy"]["lower_edge"]
        sell_upper = market_settings[market]["condition_coefs"]["sell"]["upper_edge"]
        sell_lower = market_settings[market]["condition_coefs"]["sell"]["lower_edge"]
        while True:
            if (self.buy_price < self.bin_symbol_cli.get_bid()*(1-buy_upper) or self.buy_price > self.bin_symbol_cli.get_bid()*(1-buy_lower)) or \
                (self.sell_price < self.bin_symbol_cli.get_ask()*(1+sell_lower) or self.sell_price > self.bin_symbol_cli.get_ask()*(1+sell_upper)):
                self.bin_symbol_checker_action()
            sleep(0.01)

    def bin_symbol_checker_action(self):
        print(outils.colorize_text("price changed", 'purple'))
        print("Top order's prices was", self.buy_price, self.sell_price)
        print()
        self.check_event.set()
        self.price_event.clear()
        self.price_event.wait()


class Instance:
    market: str
    base_balance: float # coin balance
    symbol: str
    market_id: str
    injective_trader: DerivativeInjectiveTrader
    inj_pos_cli: PositionRedisClient
    condition_manager: ConditionManager
    bin_symbol_cli: FuturesSymbolClient
    wallet_key: str
    subaccount_id: str
    def __init__(self, market: str, base_balance: float, inj_wallet: dict) -> None:
        self.market = market
        self.base_balance = base_balance
        self.symbol = market+"USDT" 
        self.market_id = inj_derivative_markets[market]['market_id']
        self.symbol = market+"USDT"
        self.wallet_key = inj_wallet["wallet_key"]
        self.subaccount_id = inj_wallet["subaccount_id"]
        self.inj_pos_cli = PositionRedisClient(
            self.market_id,
            redis.Redis(
                redis_confs.HOST,
                redis_confs.PORT,
                redis_confs.DBS['primary']
            )
        )

        self.bin_symbol_cli = FuturesSymbolClient(
            self.symbol,
            redis.Redis(
                redis_confs.HOST,
                redis_confs.PORT,
                redis_confs.DBS['primary']
            )
        )


    def cal_safe_balance(self, theter_balance: float, btc_price: float, leverage: int) -> float:
        return theter_balance / 2 / btc_price * (leverage - 1)
    
    def get_edited_contrib_params(self) -> dict:
        contrib_params = der_contrib_params[self.market]
        contrib_params = [contrib_params[i] 
                          for i in range(len(contrib_params)) 
                          if i not in market_settings[self.market]["excluding_orders"]]
        contrib_params[0] = (contrib_params[0][0], contrib_params[0][1] * FIRST_ORDER_MULTIPLIER)
        contrib_params.insert(
            2, 
            (
                (contrib_params[1][0]+contrib_params[2][0])/2, 
                (contrib_params[1][1]+contrib_params[2][1])/2
            )
        )
        contrib_params.insert(
            1,
            (
                (contrib_params[0][0]+contrib_params[1][0])/2, 
                (contrib_params[0][1]+contrib_params[1][1])/2
            )
        )
        return contrib_params

    def get_edited_contrib_params_based_on_quantity(self, base_quantity) -> dict:
        if base_quantity <= 0:
            return []
        contrib_params = self.get_edited_contrib_params()
        mid_price = self.bin_symbol_cli.get_ask() + self.bin_symbol_cli.get_bid()
        mid_price /= 2
        weight_sum = sum([(1/x[1]) for i,x in enumerate(contrib_params) if i >= RISK_ORDER_NO])
        q = ((1/contrib_params[RISK_ORDER_NO][1]) / weight_sum) * (base_quantity - RISK_ORDER_NO*RISK_ORDER_TETHER/mid_price) * mid_price
        while q < MIN_ORDER_TETHER and len(contrib_params) > RISK_ORDER_NO:
            del contrib_params[-1]
            if not len(contrib_params) > RISK_ORDER_NO:
                return []
            weight_sum = sum([(1/x[1]) for i,x in enumerate(contrib_params) if i >= RISK_ORDER_NO])
            q = ((1/contrib_params[RISK_ORDER_NO][1]) / weight_sum) * (base_quantity - RISK_ORDER_NO*RISK_ORDER_TETHER/mid_price) * mid_price
        if not len(contrib_params) > RISK_ORDER_NO:
            return []
        return contrib_params

    def get_reordering_quantities(self, prices, contrib_params, base_quantity) -> list:
        multipliers = [x[1] for i,x in enumerate(contrib_params) if i >= RISK_ORDER_NO]
        weight_sum = sum([(1/m) for m in multipliers])
        mid_price = sum(self.bin_symbol_cli.get_ask_bid())/2
        quantities = [
            (1/m)*(base_quantity - RISK_ORDER_NO*RISK_ORDER_TETHER/mid_price)/weight_sum 
            for m in multipliers]
        quantities = [RISK_ORDER_TETHER/prices[i] for i in range(RISK_ORDER_NO)] + quantities
        quantities = [round(q, market_settings[self.market]['round_decis']) for q in quantities]
        return quantities

    def get_buy_reordering_prices(self, contrib_params) -> list:
        the_price = self.bin_symbol_cli.get_bid()
        edges = [x[0] for x in contrib_params]
        prices = [the_price*(1-e) for e in edges]
        prices = [outils.truncate(p, market_settings[self.market]["price_round_decis"]) for p in prices]
        return prices

    def get_sell_reordering_prices(self, contrib_params) -> list:
        the_price = self.bin_symbol_cli.get_ask()
        edges = [x[0] for x in contrib_params]
        prices = [the_price*(1+e) for e in edges]
        prices = [outils.truncate_up(p, market_settings[self.market]["price_round_decis"]) for p in prices]
        return prices
    
    async def reorder(self):
        short, long = self.inj_pos_cli.get_position_quantity()
        print("positions: long =", long, ", short =", short)
        buy_base = self.base_balance / 2 + short - long
        sell_base = self.base_balance / 2 - short + long
        buy_contrib_params = self.get_edited_contrib_params_based_on_quantity(buy_base)
        sell_contrib_params = self.get_edited_contrib_params_based_on_quantity(sell_base)

        buy_prices = self.get_buy_reordering_prices(
            buy_contrib_params)
        sell_prices = self.get_sell_reordering_prices(
            sell_contrib_params)

        buy_quantities = self.get_reordering_quantities(
            buy_prices,
            buy_contrib_params,
            buy_base)
        sell_quantities = self.get_reordering_quantities(
            sell_prices,
            sell_contrib_params,
            sell_base)

        print("contribution params are")
        print("buy", buy_contrib_params)
        print("sell", sell_contrib_params)

        print("REORDERING")
        buy_orders = [
            {
                'price': buy_prices[i],
                'quantity': buy_quantities[i],
                'is_buy': True,
                'is_po': POST_ONLY
            } for i in range(len(buy_prices))
        ]

        sell_orders = [
            {
                'price': sell_prices[i],
                'quantity': sell_quantities[i],
                'is_buy': False,
                'is_po': POST_ONLY
            } for i in range(len(sell_prices))
        ]

        orders_params = buy_orders + sell_orders
        pprint.pprint(orders_params)
        pprint.pprint(self.bin_symbol_cli.get_ask_bid())
        res = await self.injective_trader.batch_update(
            self.market_id,
            orders_params,
            LEVERAGE
        )
        print("result is ")
        pprint.pprint(res)
        return [buy_prices[0], sell_prices[0]]

    async def run(self):
        self.injective_trader = await DerivativeInjectiveTrader.create(
            self.wallet_key, seq_share=False
        )
        self.condition_manager = ConditionManager(
            self.bin_symbol_cli
        )
        print("Starting now")
        self.condition_manager.start(self.market)
        # while True:
        print("waiting for coroutines ...")
        sleep(4)
        try:
            prices = await self.reorder()
            sleep(0.4)
            while True:
                self.condition_manager.check(prices)
                prices = await self.reorder()
                sleep(0.4)
        except Exception as e:
            print(e)
            print("Dropped Trying again.")
            await self.injective_trader.cancel_orders(self.market_id)
            raise e


if __name__ == "__main__":
    print("HI: ")
    print("-"*50)
    sys_args = outils.prompt_sys_for_args()
    wallet_number = int(sys_args[1])
    market = sys_args[2]
    inj_wallet = WALLETS[wallet_number]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    base_balance = market_settings[market]['base_balance']
    instance = Instance(market, base_balance, inj_wallet)
    print("waiting for cachers to wake up")
    sleep(10)
    loop.run_until_complete(instance.run())