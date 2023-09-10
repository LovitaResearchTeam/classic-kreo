def injective_position_hash(market_id: str) -> str:
    return f"position_{market_id[:10]}"


def injective_balance_hash(denom: str) -> str:
    return f"inj_balance_{denom[:10]}"


def injective_portfolio_hash(denom: str) -> str:
    return f"inj_portfolio_{denom[:10]}"


def binance_asset_hash() -> str:
    return "binance_balances"


def injective_spot_orderbook_hash(market_id: str) -> str:
    return f"inj_spot_orderbook_{market_id[:10]}"


def injective_derivative_orderbook_hash(market_id: str) -> str:
    return f"inj_der_orderbook_{market_id[:10]}"


def binance_spot_symbol_hash(symbol: str) -> str:
    return f"binance_spot_symbol_bid_ask_{symbol}"


def binance_futures_symbol_hash(symbol: str) -> str:
    return f"binance_futures_symbol_bid_ask_{symbol}"


def autopilot_binance_balance_hash(asset: str) -> str:
    return f"binance_balance_ap_{asset}"


def autopilot_injective_position_hash(asset: str) -> str:
    return f"injective_position_ap_{asset}"


def autopilot_injective_balance_hash(asset: str) -> str:
    return f"injective_balance_ap_{asset}"