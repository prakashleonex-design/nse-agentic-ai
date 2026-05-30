from __future__ import annotations

from nse_agentic_trader.config import Settings
from nse_agentic_trader.models import OrderRequest, OrderResult


class AngelSmartApiBroker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = None

    def connect(self) -> None:
        if not self.settings.live_orders_enabled:
            raise RuntimeError("Live Angel connection blocked. Set TRADING_MODE=live and ALLOW_LIVE_ORDERS=true.")

        try:
            from SmartApi import SmartConnect
            import pyotp
        except ImportError as exc:
            raise RuntimeError("Install SmartAPI support with: pip install -e .[angel]") from exc

        self.client = SmartConnect(api_key=self.settings.angel_api_key)
        otp = pyotp.TOTP(self.settings.angel_totp_secret).now()
        session = self.client.generateSession(
            self.settings.angel_client_code,
            self.settings.angel_password,
            otp,
        )
        if not session.get("status"):
            raise RuntimeError(f"Angel login failed: {session}")

    def place_order(self, order: OrderRequest) -> OrderResult:
        if not self.settings.live_orders_enabled:
            return OrderResult(False, None, "Live order blocked by configuration")
        if self.client is None:
            self.connect()

        params = {
            "variety": self.settings.default_order_variety,
            "tradingsymbol": order.symbol,
            "symboltoken": order.symboltoken or "",
            "transactiontype": order.side.value,
            "exchange": order.exchange or self.settings.default_exchange,
            "ordertype": order.order_type,
            "producttype": order.product_type,
            "duration": "DAY",
            "price": order.price or "0",
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(order.quantity),
        }
        result = self.client.placeOrder(params)
        return OrderResult(True, str(result), "Live Angel order submitted")
