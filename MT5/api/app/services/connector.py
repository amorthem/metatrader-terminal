import MetaTrader5 as mt5
import logging
import os
import threading
from app.utils.exceptions import MT5ConnectionError
from app.utils.config import settings

logger = logging.getLogger(__name__)

LOGIN_MARKER = "/tmp/login_complete"
MT5_PATH = "C:\\Metatrader-5\\terminal64.exe"


class MT5Connector:
    """MT5 connection manager.

    Waits for auto-login to create LOGIN_MARKER, then calls
    mt5.initialize() in a background thread. The blocking call
    is safe at that point because MT5 is already logged in and
    the IPC pipe should connect quickly.
    """

    def __init__(self):
        self._initialized = False
        self._initializing = False
        self._lock = threading.Lock()

    @staticmethod
    def _login_ready() -> bool:
        return os.path.exists(LOGIN_MARKER)

    def _do_initialize(self):
        """Blocking init — runs in a background thread after marker exists."""
        try:
            logger.info("MT5 initialization started (background thread)...")
            success = mt5.initialize(MT5_PATH, portable=True)
            if success:
                self._initialized = True
                logger.info("MT5 initialized successfully")
            else:
                error_code, error_msg = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error_msg} ({error_code})")
        except Exception as e:
            logger.exception(f"MT5 initialization crashed: {e}")
        finally:
            self._initializing = False

    def _start_init(self):
        """Kick off background init if marker exists and not already running."""
        with self._lock:
            if self._initialized or self._initializing:
                return
            if not self._login_ready():
                return
            self._initializing = True
            thread = threading.Thread(target=self._do_initialize, daemon=True)
            thread.start()

    def initialize(self) -> bool:
        """Ensure MT5 is connected. Returns True or raises MT5ConnectionError."""
        if self._initialized:
            return True

        if self._initializing:
            raise MT5ConnectionError(
                "MT5 is still connecting — try again shortly"
            )

        if not self._login_ready():
            raise MT5ConnectionError(
                "Waiting for MT5 auto-login to complete"
            )

        # Marker exists but not yet initialized — kick off background init
        self._start_init()
        raise MT5ConnectionError(
            "MT5 initialization started — try again shortly"
        )

    def get_terminal_info(self):
        self.initialize()
        return mt5.terminal_info()

    def get_account_info(self):
        self.initialize()
        return mt5.account_info()


mt5_connector = MT5Connector()
