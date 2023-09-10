depricating_derivative_market_confs = {
    'BTC' : {
        "base_amount": 0.001,
        "round_decis": 3,
        "market_id": "0x4ca0f92fc28be0c9761326016b5a1a2177dd6375558365116b5bdda9abc229ce"
        },
    'ETH' :{
        "base_amount": 0.03,
        "round_decis": 2,
        "market_id": "0x54d4505adef6a5cef26bc403a33d595620ded4e15b9e2bc3dd489b714813366a"
    },
    'USDT': {
        "denom": "peggy0xdAC17F958D2ee523a2206206994597C13D831ec7"
    },
}

spot_market_confs = {
    'ATOM': {
        "base_amount": 5,
        "round_decis": 2,
        "market_id": "0x0511ddc4e6586f3bfe1acb2dd905f8b8a82c97e1edaef654b12ca7e6031ca0fa",
        "denom": "ibc/C4CFF46FD6DE35CA4CF4CE031E643C8FDC9BA4B99AE598E9B0ED98FE3A2319F9",
    },
    'USDT': {
        "denom": "peggy0xdAC17F958D2ee523a2206206994597C13D831ec7"
    },
    'INJ': {
        "base_amount": 12,
        "round_decis": 1,
        "market_id": "0xa508cb32923323679f29a032c70342c147c17d0145625922b0ef22e955c844c0",
        "denom": "inj",
        "decimals": 12
    },
}

inj_derivative_market_confs = {
    'BTC': {
        'market_id': "0x4ca0f92fc28be0c9761326016b5a1a2177dd6375558365116b5bdda9abc229ce",
        'base_decimals': 0,
        'qoute_decimals': 6,
    },
    'ETH': {
        'market_id': "0x54d4505adef6a5cef26bc403a33d595620ded4e15b9e2bc3dd489b714813366a",
        'base_decimals': 0,
        'quote_decimals': 6
    },
    'BNB': {
        'market_id': "0x1c79dac019f73e4060494ab1b4fcba734350656d6fc4d474f6a238c13c6f9ced",
        'base_decimals': 0,
        'quote_decimals': 6
    },
    'INJ': {
        'market_id': "0x9b9980167ecc3645ff1a5517886652d94a0825e54a77d2057cbbe3ebee015963",
        'base_decimals': 0,
        'quote_decimals': 6
    },
    'ATOM': {
        'market_id': "0xc559df216747fc11540e638646c384ad977617d6d8f0ea5ffdfc18d52e58ab01",
        'base_decimals': 0,
        'quote_decimals': 6
    }
}

inj_spot_market_confs = {
    'ATOM': {
        'market_id': "0x0511ddc4e6586f3bfe1acb2dd905f8b8a82c97e1edaef654b12ca7e6031ca0fa",
        'base_decimals': 6,
        'quote_decimals': 6
    },
    'INJ': {
        'market_id': "0xfbc729e93b05b4c48916c1433c9f9c2ddb24605a73483303ea0f87a8886b52af",
        'base_decimals': 18,
        'quote_decimals': 6
    }
}
