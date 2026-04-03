import MetaTrader5 as mt5
import logging
import os
import threading
from app.utils.exceptions import MT5ConnectionError
from app.utils.config import settings

logger = logging.getLogger(__name__)

LOGIN_MARKER = "/tmp/login_complete"


class MT5Connector:
    def __init__(self):
        self._initialized = False
        self._initializing = False
        self._lock = threading.Lock()
        self._init_thread: threading.Thread = None

    @staticmethod
    def _login_ready() -> bool:
        """Check if auto-login has confirmed MT5 is connected."""
        return os.path.exists(LOGIN_MARKER)

    def _do_initialize(self):
        """Blocking init — runs in a background thread.
        Only called after auto-login has confirmed MT5 is connected,
        so mt5.initialize() should succeed quickly without blocking
        wineserver for 80s."""
        try:
            logger.info("MT5 initialization started (background thread)...")
            success = mt5.initialize("C:\\Metatrader-5\\terminal64.exe", portable=True)
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

    def start_init(self):
        """Kick off initialization in a background thread (non-blocking).
        Will not start until the auto-login marker file exists."""
        with self._lock:
            if self._initialized or self._initializing:
                return
            if not self._login_ready():
                return
            self._initializing = True
            self._init_thread = threading.Thread(
                target=self._do_initialize, daemon=True
            )
            self._init_thread.start()

    def initialize(self) -> bool:
        """Ensure MT5 is connected. Returns True or raises MT5ConnectionError.

        Will not call mt5.initialize() until the auto-login marker exists,
        preventing the blocking C call from starving wineserver/uvicorn.
        """
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

        # Login marker exists but not yet initialized — kick off background init
        self.start_init()
        raise MT5ConnectionError(
            "MT5 initialization started — try again shortly"
        )

    def connect(self, login: int, password: str, server: str, timeout: int = 60):
        """Switch account — blocks the calling thread but runs mt5.initialize
        in a worker thread so the GIL is released between attempts and uvicorn
        can still serve other requests on its other threads."""
        import concurrent.futures

        mt5.shutdown()
        self._initialized = False
        self._initializing = False

        def _do_connect():
            return mt5.initialize(
                "C:\\Metatrader-5\\terminal64.exe",
                login=login, password=password, server=server, portable=True
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_do_connect)
            try:
                success = future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise MT5ConnectionError("MT5 connection timed out")

        if not success:
            error_code, error_msg = mt5.last_error()
            raise MT5ConnectionError(
                f"MT5 connection failed: {error_msg}",
                code=error_code
            )

        self._initialized = True
        logger.info(f"MT5 connected: login={login} server={server}")
        return True

    def get_terminal_info(self):
        """Get terminal information including broker details."""
        self.initialize()
        return mt5.terminal_info()

    def get_account_info(self):
        """Get account information including broker details."""
        self.initialize()
        return mt5.account_info()


mt5_connector = MT5Connector()
