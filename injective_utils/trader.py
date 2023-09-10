import asyncio
import redis
#
from pyinjective.composer import Composer as ProtoMsgComposer
from pyinjective.async_client import AsyncClient
from pyinjective.transaction import Transaction
from pyinjective.constant import Network
from pyinjective.wallet import PrivateKey
from pyinjective.wallet import Address
from google.protobuf.json_format import MessageToDict

#
import utils.outils as outils
from injective_utils.cachers import DerivativeOrderbookCacher
from settings.other import INJECTIVE_NETWORK
from configs import redis as redis_confs
#
from math import ceil


class BadOrderHashException(Exception):
    pass 


class SequenceManager:
    network: Network
    address: Address
    _address_object: object
    _sequence_number: int

    def __init__(self, address: Address, network: Network) -> None:
        self.address = address
        self.network = network
        self._sequence_number = None

    def fetch(self):
        self.address.init_num_seq(self.network.lcd_endpoint)
        sequence_number = self.address.get_sequence()
        self._sequence_number = sequence_number
        print("Sequence fetched from network:", self._sequence_number)
        return sequence_number

    def get(self):
        if self._sequence_number is None:
            self.fetch()
        return self._sequence_number

    def incr(self):
        self._sequence_number += 1

    @staticmethod
    def create(address: Address, network: Network, seq_share):
        if seq_share:
            return SequenceSharingSequenceManager(address, network)
        return SequenceManager(address, network)


class SequenceSharingSequenceManager(SequenceManager):
    _redis: redis.Redis
    def __init__(self, address: Address, network: Network) -> None:
        super().__init__(address, network)
        self._redis = redis.Redis(
            redis_confs.HOST,
            redis_confs.PORT,
            redis_confs.DBS["primary"]
        )

    def fetch(self):
        sequence_number = super().fetch()
        self._redis.set("sequence", sequence_number)
        return sequence_number

    def get(self):
        seq = self._redis.get("sequence")
        if seq is None:
            sequence_number = self.fetch()
            return sequence_number
        return int(seq)

    def incr(self):
        seq = self._redis.get("sequence")
        if seq is None:
            self.fetch()
        else:
            self._redis.incr("sequence", 1)


class TXManager:
    pub_key: object
    priv_key: object
    client: object
    sequence_manager: SequenceManager
    network: object
    composer: object

    def __init__(self, pub_key, priv_key, client: AsyncClient, sequence_manager: SequenceManager,
                 network: Network, composer: ProtoMsgComposer) -> None:
        self.pub_key = pub_key
        self.priv_key = priv_key
        self.client = client
        self.sequence_manager = sequence_manager
        self.network = network
        self.composer = composer

    async def broadcast_tx(self, msg, orderhash_checker=None):
        print("start broadcast")
        tx = self._make_tx(msg)
        sim_res, sim_res_msg = await self._simulate_tx(tx)
        if orderhash_checker is not None:
            await orderhash_checker(sim_res_msg)

        tx = self._gasify_tx(tx, sim_res)

        sign_doc = tx.get_sign_doc(self.pub_key)
        sig = self.priv_key.sign(sign_doc.SerializeToString())
        tx_raw_bytes = tx.get_tx_data(sig, self.pub_key)

        res = await self.client.send_tx_async_mode(tx_raw_bytes)
        print(outils.colorize_text(
            "---Injective Transaction Response---", 'green'))
        self.sequence_manager.incr()
        print("transaction broadcasted and sequence increased to", self.sequence_manager.get())
        return res, sim_res_msg

    def _make_tx(self, msg):
        tx = (
            Transaction()
            .with_messages(msg)
            .with_sequence(self.sequence_manager.get())
            .with_account_num(self.client.get_number())
            .with_chain_id(self.network.chain_id)
        )
        return tx

    async def _simulate_tx(self, tx):
        sim_sign_doc = tx.get_sign_doc(self.pub_key)
        sim_sig = self.priv_key.sign(sim_sign_doc.SerializeToString())
        sim_tx_raw_bytes = tx.get_tx_data(sim_sig, self.pub_key)
        
        (sim_res, success) = await self.client.simulate_tx(sim_tx_raw_bytes)
        if not success:
            raise sim_res
        sim_res_msg = ProtoMsgComposer.MsgResponses(
            sim_res.result.data, simulation=True)
        print("---Simulation Response---")
        return sim_res, sim_res_msg

    def _gasify_tx(self, tx, sim_res):
        gas_price = 800000000
        gas_limit = int(ceil(sim_res.gas_info.gas_used * 1.4))
        gas_fee = '{:.18f}'.format((gas_price * gas_limit) / pow(10, 18)).rstrip('0')
        fee = [self.composer.Coin(
            amount=gas_price * gas_limit,
            denom=self.network.fee_denom,
        )]
        new_tx = tx.with_gas(gas_limit).with_fee(fee).with_memo(
            '').with_timeout_height(self.client.timeout_height)
        return new_tx

    async def _handle_exceptions(self, ex):
        if "account sequence mismatch" in str(ex):
            await self._handle_sequence_mismatch(ex)
        else:
            print("____ Error occured making tx ____")
            print(ex)
            return False

    async def _handle_sequence_mismatch(self, ex):
        print(ex)
        print(f"____ Sequence mismatch {self.sequence_manager.get()}: Trying again 3 seconds later again ____")
        self.sequence_manager.fetch()
        await asyncio.sleep(3)
        print("Fetched:", self.sequence_manager.get())


class DerivativeInjectiveTrader:
    network: Network
    address: Address
    client: AsyncClient
    priv_key: PrivateKey
    pub_key: str
    composer: ProtoMsgComposer
    subaccount_id: str
    sequence_manager: SequenceManager
    tx_manager: TXManager

    def __init__(self, network: Network, account_address: Address,
                 client: AsyncClient, priv_key, pub_key, composer,
                 subaccount_id, seq_share: bool) -> None:
        self.network = network
        self.address = account_address
        self.client = client
        self.priv_key = priv_key
        self.pub_key = pub_key
        self.composer = composer
        self.subaccount_id = subaccount_id
        self.sequence_manager = SequenceManager.create(
            account_address, network, seq_share
        )
        self.sequence_manager.get()
        self.tx_manager = TXManager(
            pub_key, priv_key, client,
            self.sequence_manager, network, composer
        )

    @classmethod
    async def create(cls, wallet_key, seq_share: bool = False):
        network = cls.get_network()
        composer = ProtoMsgComposer(network=network.string())

        client = AsyncClient(network, insecure=False if INJECTIVE_NETWORK == "mainnet" else True)
        await client.sync_timeout_height()

        priv_key = PrivateKey.from_hex(wallet_key)
        pub_key = priv_key.to_public_key()
        address = pub_key.to_address()
        account = await client.get_account(address.to_acc_bech32())
        subaccount_id = address.get_subaccount_id(index=0)
        return cls(network, address, client, priv_key, 
                   pub_key, composer, subaccount_id, seq_share)
    
    @staticmethod
    def get_network():
        if INJECTIVE_NETWORK == "mainnet":
            return Network.mainnet()
        if INJECTIVE_NETWORK == "local":
            return Network.local()
        return Network.custom(
            lcd_endpoint=f'http://{INJECTIVE_NETWORK}:10337',
            tm_websocket_endpoint=f'ws://{INJECTIVE_NETWORK}:26657/websocket',
            grpc_endpoint=f'{INJECTIVE_NETWORK}:9900',
            grpc_exchange_endpoint=f'{INJECTIVE_NETWORK}:9910',
            grpc_explorer_endpoint=f'{INJECTIVE_NETWORK}:9911',
            chain_id='injective-1',
            env='mainnet'
        )

    async def buy_limit(self, market_id, price, quantitiy, leverage=1):
        return await self._trade_limit(market_id, price, quantitiy, leverage=leverage)

    async def sell_limit(self, market_id, price, quantitiy, leverage=1):
        return await self._trade_limit(market_id, price, quantitiy, leverage=leverage, is_buy=False)

    async def _trade_limit(self, market_id, price, quantity, is_buy=True, leverage=1):
        while True:
            try:
                msg = self.composer.MsgCreateDerivativeLimitOrder(
                    sender=self.address.to_acc_bech32(),
                    market_id=market_id,
                    subaccount_id=self.subaccount_id,
                    fee_recipient=self.address.to_acc_bech32(),
                    price=price,
                    quantity=quantity,
                    leverage=leverage,
                    is_buy=is_buy
                )
                return await self.tx_manager.broadcast_tx(msg)
            except Exception as ex:
                await self._handle_exceptions(ex)

    async def update_buy_limit(self, market_id, price, quantity, leverage=1):
        return await self._update_trade_limit(market_id, price, quantity, leverage=leverage, is_buy=True)

    async def update_sell_limit(self, market_id, price, quantity, leverage=1):
        return await self._update_trade_limit(market_id, price, quantity, leverage=leverage, is_buy=False)

    async def _update_trade_limit(self, market_id, price, quantity, is_buy=True, leverage=1):
        while True:
            try:
                derivative_orders_to_create = [
                    self.composer.DerivativeOrder(
                        market_id=market_id,
                        subaccount_id=self.subaccount_id,
                        fee_recipient=self.address.to_acc_bech32(),
                        price=price,
                        quantity=quantity,
                        leverage=leverage,
                        is_buy=is_buy,
                        is_po=False
                    )
                ]
                msg = self.composer.MsgBatchUpdateOrders(
                    sender=self.address.to_acc_bech32(),
                    derivative_orders_to_create=derivative_orders_to_create,
                    subaccount_id=self.subaccount_id,
                    derivative_market_ids_to_cancel_all=[market_id]
                )
                return await self.tx_manager.broadcast_tx(msg)
            except Exception as ex:
                await self._handle_exceptions(ex)

    async def buy_market(self, market_id, price, quantitiy, leverage=1):
        return await self._trade_market(market_id, price, quantitiy, leverage=leverage)

    async def sell_market(self, market_id, price, quantitiy, leverage=1):
        return await self._trade_market(market_id, price, quantitiy, is_buy=False, leverage=leverage)

    async def _trade_market(self, market_id, price, quantity, is_buy=True, leverage=1):
        while True:
            try:
                msg = self.composer.MsgCreateDerivativeMarketOrder(
                    sender=self.address.to_acc_bech32(),
                    market_id=market_id,
                    subaccount_id=self.subaccount_id,
                    fee_recipient=self.address.to_acc_bech32(),
                    price=price,
                    quantity=quantity,
                    leverage=leverage,
                    is_buy=is_buy
                )
                return await self.tx_manager.broadcast_tx(msg)
            except Exception as ex:
                await self._handle_exceptions(ex)

    async def batch_update(self, market_id: str, orders_params: tuple, leverage=1):
        while True:
            try:
                derivative_orders_to_create = [
                    self.composer.DerivativeOrder(
                        market_id=market_id,
                        subaccount_id=self.subaccount_id,
                        fee_recipient=self.address.to_acc_bech32(),
                        price=o['price'],
                        quantity=o['quantity'],
                        leverage=leverage,
                        is_buy=o['is_buy'],
                        is_po=o['is_po']
                    ) for o in orders_params
                ]
                msg = self.composer.MsgBatchUpdateOrders(
                    sender=self.address.to_acc_bech32(),
                    derivative_orders_to_create=derivative_orders_to_create,
                    subaccount_id=self.subaccount_id,
                    derivative_market_ids_to_cancel_all=[market_id]
                )

                async def hash_checker(sim_res):
                    if sim_res[0].derivative_order_hashes:
                        for oh in sim_res[0].derivative_order_hashes:
                            if len(oh) > 5:
                                return
                        await self.cancel_orders(market_id)
                        raise BadOrderHashException("Orderhashes are not ok")
                res = await self.tx_manager.broadcast_tx(msg, hash_checker)
                return res
            except Exception as ex:
                await self._handle_exceptions(ex)

    async def cancel_orders(self, market_id: str):
        try:
            msg = self.composer.MsgBatchUpdateOrders(
                sender=self.address.to_acc_bech32(),
                subaccount_id=self.subaccount_id,
                derivative_market_ids_to_cancel_all=[market_id]
            )
            return await self.tx_manager.broadcast_tx(msg)
        except Exception as ex:
            await self._handle_exceptions(ex)

    async def cancel_order(self, market_id: str, order_hash):
        try:
            msg = self.composer.MsgCancelDerivativeOrder(
                sender=self.address.to_acc_bech32(),
                market_id=market_id,
                subaccount_id=self.subaccount_id,
                order_hash=order_hash
            )
            return await self.tx_manager.broadcast_tx(msg)
        except Exception as ex:
            await self._handle_exceptions(ex)

    async def close_positions(self, market_id, epsilon, ob_cacher: DerivativeOrderbookCacher):
        position_list = await self.client.get_derivative_positions(
            market_id=market_id,
            subaccount_id=self.subaccount_id,
        )
        while (position_list.positions):
            position = position_list.positions[0]
            quantity = position.quantity
            try:
                if position.direction == 'long':
                    sell_price = ob_cacher.get_highest_buyer() * (1 - epsilon)
                    await self.sell_limit(market_id, sell_price, float(quantity))
                else:
                    buy_price = ob_cacher.get_lowest_seller() * (1 + epsilon)
                    await self.buy_limit(market_id, buy_price, float(quantity))

                await asyncio.sleep(4)
                position_list = await self.client.get_derivative_positions(
                    market_id=market_id,
                    subaccount_id=self.subaccount_id,
                )
                await asyncio.sleep(4)
            except Exception as ex:
                await self._handle_exceptions(ex)

    async def _handle_exceptions(self, ex):
        if "account sequence mismatch" in str(ex):
            await self._handle_sequence_mismatch(ex)
        else:
            print("____ Error occured making tx ____")
            print(ex)
            raise ex

    async def _handle_sequence_mismatch(self, ex):
        print(ex)
        print(f"____ Sequence mismatch {self.sequence_manager.get()}: Trying again 3 seconds later again ____")
        local_seq = self.sequence_manager.get()
        fetched_seq = self.sequence_manager.fetch()
        print("my sequence was", local_seq, "sequence from network is", fetched_seq)
        await asyncio.sleep(3)
        print("Fetched:", self.sequence_manager.get())


class SpotInjectiveTrader(DerivativeInjectiveTrader):
    async def _trade_limit(self, market_id, price, quantity, is_buy=True, **kwargs):
        while True:
            try:
                msg = self.composer.MsgCreateSpotLimitOrder(
                    sender=self.address.to_acc_bech32(),
                    market_id=market_id,
                    subaccount_id=self.subaccount_id,
                    fee_recipient=self.address.to_acc_bech32(),
                    price=price,
                    quantity=quantity,
                    is_buy=is_buy
                )
                return await self.tx_manager.broadcast_tx(msg)
            except Exception as ex:
                await self._handle_exceptions(ex)

    async def _update_trade_limit(self, market_id, price, quantity, is_buy=True, **kwargs):
        while True:
            try:
                spot_orders_to_create = [
                    self.composer.SpotOrder(
                        market_id=market_id,
                        subaccount_id=self.subaccount_id,
                        fee_recipient=self.address.to_acc_bech32(),
                        price=price,
                        quantity=quantity,
                        is_buy=is_buy,
                        is_po=False
                    )
                ]
                msg = self.composer.MsgBatchUpdateOrders(
                    sender=self.address.to_acc_bech32(),
                    spot_orders_to_create=spot_orders_to_create,
                    subaccount_id=self.subaccount_id,
                    spot_market_ids_to_cancel_all=[market_id]
                )
                return await self.tx_manager.broadcast_tx(msg)
            except Exception as ex:
                await self._handle_exceptions(ex)

    async def _trade_market(self, market_id, price, quantity, is_buy=True, **kwargs):
        while True:
            try:
                msg = self.composer.MsgCreateSpotMarketOrder(
                    sender=self.address.to_acc_bech32(),
                    market_id=market_id,
                    subaccount_id=self.subaccount_id,
                    fee_recipient=self.address.to_acc_bech32(),
                    price=price,
                    quantity=quantity,
                    is_buy=is_buy
                )
                return await self.tx_manager.broadcast_tx(msg)
            except Exception as ex:
                await self._handle_exceptions(ex)
    
    async def cancel_orders(self, market_id: str):
        try:
            msg = self.composer.MsgBatchUpdateOrders(
                sender=self.address.to_acc_bech32(),
                subaccount_id=self.subaccount_id,
                spot_market_ids_to_cancel_all=[market_id]
            )
            return await self.tx_manager.broadcast_tx(msg)
        except Exception as ex:
            await self._handle_exceptions(ex)

    async def cancel_order(self, market_id: str, order_hash):
        try:
            msg = self.composer.MsgCancelSpotOrder(
                sender=self.address.to_acc_bech32(),
                market_id=market_id,
                subaccount_id=self.subaccount_id,
                order_hash=order_hash
            )
            return await self.tx_manager.broadcast_tx(msg)
        except Exception as ex:
            await self._handle_exceptions(ex)
