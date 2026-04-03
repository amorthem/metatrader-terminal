import MetaTrader5 as mt5
import logging
from app.utils.exceptions import MT5ConnectionError
from app.utils.config import settings

logger = logging.getLogger(__name__)

class MT5Connector:
    def __init__(self):
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize connection to MT5 terminal. Raises MT5ConnectionError on failure."""
        if not self._initialized:
            success = mt5.initialize(timeout=30000)
            if success:
                self._initialized = True
                logger.info("MT5 initialized successfully")
                return True
            else:
                error_code, error_msg = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error_msg} ({error_code})")
                raise MT5ConnectionError(
                    f"MT5 initialization failed: {error_msg}",
                    code=error_code
                )
        return True

    def get_terminal_info(self):
        """Get terminal information including broker details."""
        if not self._initialized:
            self.initialize()
        return mt5.terminal_info()

    def get_account_info(self):
        """Get account information including broker details."""
        if not self._initialized:
            self.initialize()
        return mt5.account_info()

mt5_connector = MT5Connector()
