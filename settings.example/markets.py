market_settings = {
    'BTC' : {
        "round_decis": 3,
        "price_round_decis": 1,
        "base_balance": 3,
        "condition_coefs": {
            "buy": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            },
            "sell": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            }
        },
        "excluding_orders": set([0])
    },
    'ETH' :{
        "round_decis": 2,
        "price_round_decis": 2,
        "base_balance": 0.5,
        "condition_coefs": {
            "buy": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            },
            "sell": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            }
        },
        "excluding_orders": set([0])
    },
    'ATOM' :{
        "round_decis": 2,
        "price_round_decis": 3,
        "base_balance": 8000,
        "condition_coefs": {
            "buy": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            },
            "sell": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            }
        },
        "excluding_orders": set([])
    },
    'INJ' :{
        "round_decis": 1,
        "price_round_decis": 3,
        "base_balance": 0.02,
        "condition_coefs": {
            "buy": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            },
            "sell": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            }
        },
        "excluding_orders": set([0,1])
    },
    'BNB' :{
        "round_decis": 2,
        "price_round_decis": 2,
        "base_balance": 10,
        "condition_coefs": {
            "buy": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            },
            "sell": {
                "upper_edge": 0.0065,
                "lower_edge": 0.0004
            }
        },
        "excluding_orders": set([])
    }
}