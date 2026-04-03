import MetaTrader5 as mt5
import logging
import os
from app.utils.exceptions import MT5ConnectionError
from app.utils.config import settings

logger = logging.getLogger(__name__)

LOGIN_MARKER = "/tmp/login_complete"


class MT5Connector:
    """MT5 connection manager.

    Never calls mt5.initialize() — that blocks wineserver for ~80s and
    kills all HTTP. Instead, auto-login (a separate process) handles
    initialization and creates LOGIN_MARKER when MT5 is connected.
    The server process calls mt5 functions directly once the marker exists.
    """

    def __init__(self):
        self._initialized = False

    @staticmethod
    def _login_ready() -> bool:
        return os.path.exists(LOGIN_MARKER)

    def initialize(self) -> bool:
        """Check that MT5 is ready. Never calls mt5.initialize()."""
        if self._initialized:
            return True

        if not self._login_ready():
            raise MT5ConnectionError(
                "Waiting for MT5 auto-login to complete"
            )

        # Marker exists — MT5 was initialized by auto-login process.
        # Verify we can actually talk to the terminal.
        info = mt5.terminal_info()
        if info is not None:
            self._initialized = True
            logger.info("MT5 connection verified (auto-login)")
            return True

        raise MT5ConnectionError(
            "MT5 login marker exists but terminal is not responding"
        )

    def get_terminal_info(self):
        self.initialize()
        return mt5.terminal_info()

    def get_account_info(self):
        self.initialize()
        return mt5.account_info()


mt5_connector = MT5Connector()
