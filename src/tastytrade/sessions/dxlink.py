import asyncio
import json
import logging
from asyncio import Semaphore
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from tastytrade.sessions.messages import MessageHandler
from tastytrade.sessions.sockets import WebSocketManager

QueryParams = Optional[dict[str, Any]]

logger = logging.getLogger(__name__)


CHANNEL_REQUEST = {
    "type": "CHANNEL_REQUEST",
    "service": "FEED",
    "parameters": {"contract": "AUTO"},
}
FEED_SETUP = {
    "type": "FEED_SETUP",
    "acceptAggregationPeriod": 0.1,
    "acceptDataFormat": "COMPACT",
    "acceptEventFields": {
        "Trade": ["eventType", "eventSymbol", "price", "dayVolume", "size"],
        "Quote": [
            "eventType",
            "eventSymbol",
            "bidPrice",
            "askPrice",
            "bidSize",
            "askSize",
        ],
        "Greeks": [
            "eventType",
            "eventSymbol",
            "volatility",
            "delta",
            "gamma",
            "theta",
            "rho",
            "vega",
        ],
        "Profile": [
            "eventType",
            "eventSymbol",
            "description",
            "shortSaleRestriction",
            "tradingStatus",
            "statusReason",
            "haltStartTime",
            "haltEndTime",
            "highLimitPrice",
            "lowLimitPrice",
            "high52WeekPrice",
            "low52WeekPrice",
        ],
        "Summary": [
            "eventType",
            "eventSymbol",
            "openInterest",
            "dayOpenPrice",
            "dayHighPrice",
            "dayLowPrice",
            "prevDayClosePrice",
        ],
    },
}
SUBSCRIPTION_REQUEST = {
    "type": "FEED_SUBSCRIPTION",
    "reset": True,
    "add": [
        {"type": "Trade", "symbol": "BTC/USD:CXTALP"},
        {"type": "Quote", "symbol": "BTC/USD:CXTALP"},
        {"type": "Profile", "symbol": "BTC/USD:CXTALP"},
        {"type": "Summary", "symbol": "BTC/USD:CXTALP"},
        {"type": "Trade", "symbol": "SPY"},
        {"type": "Quote", "symbol": "SPX"},
        {"type": "Profile", "symbol": "SPY"},
        {"type": "Summary", "symbol": "SPY"},
        {"type": "Quote", "symbol": f".SPXW{datetime.now().strftime('%y%m%d')}P5895"},
        {"type": "Greeks", "symbol": f".SPXW{datetime.now().strftime('%y%m%d')}P5895"},
        {"type": "Quote", "symbol": f".SPXW{datetime.now().strftime('%y%m%d')}P5885"},
        {"type": "Greeks", "symbol": f".SPXW{datetime.now().strftime('%y%m%d')}P5885"},
        {"type": "Quote", "symbol": f".SPXW{datetime.now().strftime('%y%m%d')}P5905"},
        {"type": "Greeks", "symbol": f".SPXW{datetime.now().strftime('%y%m%d')}P5905"},
    ],
}


@dataclass
class DXLinkConfig:
    keepalive_timeout: int = 60
    version: str = "0.1-DXF-JS/0.3.0"
    channel_assignment: int = 1
    max_subscriptions: int = 10
    reconnect_attempts: int = 3  # for later use
    reconnect_delay: int = 5  # for later use


class DXLinkClient:

    # @classmethod
    # @inject
    # def run(cls, credentials: Credentials):
    #     instance = cls(MessageHandler())
    #     asyncio.run(instance.connect(credentials))

    def __init__(
        self,
        websocket_manager: WebSocketManager,
        message_handler: MessageHandler = MessageHandler(),
        config: DXLinkConfig = DXLinkConfig(),
    ):
        self.websocket = websocket_manager.websocket
        self.message_handler = message_handler
        self.subscription_semaphore = Semaphore(config.max_subscriptions)

    async def request_channel(self, channel: int, request: dict[str, Any] = CHANNEL_REQUEST):
        request = request | {"channel": channel}
        await asyncio.wait_for(self.websocket.send(json.dumps(request)), timeout=5)

    async def setup_feed(self, channel: int, request: dict[str, Any] = FEED_SETUP):
        request = request | {"channel": channel}
        await asyncio.wait_for(self.websocket.send(json.dumps(request)), timeout=5)

    async def subscribe_to_feed(self, channel: int, request: dict[str, Any] = SUBSCRIPTION_REQUEST):
        request = request | {"channel": channel}
        async with self.subscription_semaphore:
            await asyncio.wait_for(
                self.websocket.send(json.dumps(request)),
                timeout=5,
            )