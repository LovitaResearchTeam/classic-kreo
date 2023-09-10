from utils.outils import prompt_sys_for_args
from utils.ecosystem import generate_ecosystem_file
from os import system
import redis
from configs import redis as redis_confs


def check_redis_connection():
    try:
        con = redis.Redis(
            redis_confs.HOST, 
            redis_confs.PORT,
            redis_confs.DBS['primary']
        )
    except:
        raise Exception("REDIS: redis server is not up in system.")
    con.close()


def kreo(markets: list[str]):
    system("pm2 stop all")
    system("pm2 delete all")
    apps = []
    for i, market in enumerate(markets):
        apps.append({
            "name": f"binance {market}",
            "script": "./scripts/inj_bin_futures_symbol_cacher.py",
            "args": [market]
        })
        apps.append({
            "name": f"position {market}",
            "script": "./scripts/inj_pos_cacher.py",
            "args": [i, market]
        })
        apps.append({
            "name": f"equalizer {market}",
            "script": "./scripts/run_equalizer.py",
            "args": [i, market]
        })
        apps.append({
            "name": f"kreo {market}",
            "script": "./scripts/run_kreo.py",
            "args": [i, market]
        })
    generate_ecosystem_file(apps)
    system("pm2 start ecosystem.config.js")


if __name__ == "__main__":
    print("Hi. Welcome to kreo.")
    markets = prompt_sys_for_args()[1:]
    check_redis_connection()
    kreo(markets)
