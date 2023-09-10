import abc
from typing import Callable
#
from pyinjective.async_client import AsyncClient
from pyinjective.constant import Network
from google.protobuf.json_format import MessageToDict
#
from utils import outils
from configs.markets.injective import derivative_confs as inj_derivative_markets


class AbstractInjectiveSocketActioner(abc.ABC):
    action: Callable
    def __init__(self, action: Callable) -> None:
        self.action = action

    async def run(self) -> None:
        while True:
            try:
                await self._starter()
                network = Network.mainnet()
                client = AsyncClient(network, insecure=False)
                await self._run_stream(client)
            except Exception as ex:
                print(ex)
                print(outils.colorize_text("Dropped.", 'red'), "Trying again.")

    @abc.abstractmethod
    async def _run_stream(self, client) -> None:
        pass

    @abc.abstractmethod
    async def _starter(self) -> None:
        pass


class AbstractPrivateInjectiveSocketActioner(AbstractInjectiveSocketActioner):
    sub_id: str
    def __init__(self, subaccount_id: str, action) -> None:
        super().__init__(action)
        self._sub_id = subaccount_id


class DerivativeOrderHistorySocketActioner(AbstractPrivateInjectiveSocketActioner):
    _market_id: str
    def __init__(self, subaccount_id: str, market: str, action: Callable) -> None:
        super().__init__(subaccount_id, action)
        self._market_id = inj_derivative_markets[market]["market_id"]

    async def _run_stream(self, client: AsyncClient) -> None:
        subaccount = await client.stream_historical_derivative_orders(
            market_id=self._market_id,
            subaccount_id=self._sub_id,
        )
        async for msg in subaccount:
            await self.action(MessageToDict(msg)['order'])

    async def _starter(self):
        pass 


class PositionSocketActioner(AbstractPrivateInjectiveSocketActioner):
    _market_id: str
    def __init__(self, subaccount_id: str, market: str, action: Callable) -> None:
        super().__init__(subaccount_id, action)
        self._market_id = inj_derivative_markets[market]["market_id"]
    
    async def _run_stream(self, client) -> None:
        subaccount = await client.stream_derivative_positions(
                market_id=self._market_id,
                subaccount_id=self._sub_id
            )
        async for msg in subaccount:
            self.action(MessageToDict(msg.position))
    
    async def _starter(self) -> None:
        network = Network.mainnet()
        client = AsyncClient(network, insecure=False)
        positions = await client.get_derivative_positions(
            market_id=self._market_id,
            subaccount_id=self._sub_id
        )
        for position in positions.positions:
            self.action(MessageToDict(position))