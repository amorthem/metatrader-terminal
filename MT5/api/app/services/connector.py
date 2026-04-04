import MetaTrader5 as mt5
import logging
import os
import sys
import threading
from app.utils.exceptions import MT5ConnectionError
from app.utils.config import settings

logger = logging.getLogger(__name__)

LOGIN_MARKER = "/tmp/login_complete"
MT5_PATH = "C:\\Metatrader-5\\terminal64.exe"
MAX_IPC_RETRIES = 1


class MT5Connector:
    """MT5 connection manager.

    Waits for auto-login to create LOGIN_MARKER (VNC login done),
    then calls mt5.initialize() with credentials in a background
    thread to establish the IPC pipe without blocking uvicorn.

    If IPC fails after MAX_IPC_RETRIES attempts, exits the process
    so supervisor can restart the server with a fresh wineserver.
    """

    def __init__(self):
        self._initialized = False
        self._initializing = False
        self._ipc_failures = 0
        self._lock = threading.Lock()

    @staticmethod
    def _login_ready() -> bool:
        return os.path.exists(LOGIN_MARKER)

    def _do_initialize(self):
        """Blocking init — runs in a background thread after marker exists."""
        try:
            login = settings.env.MT5_LOGIN
            password = settings.env.MT5_PASSWORD
            server = settings.env.MT5_SERVER

            logger.info(f"MT5 initialization started (login={login}, server={server})...")
            success = mt5.initialize(
                MT5_PATH,
                login=login,
                password=password,
                server=server,
                portable=True,
            )
            if success:
                self._initialized = True
                self._ipc_failures = 0
                logger.info("MT5 initialized successfully")

                # Verify algo trading is enabled
                info = mt5.terminal_info()
                if info and not info.trade_allowed:
                    logger.warning(
                        "Algo trading is disabled — exiting to trigger "
                        "auto-login restart which enables it via VNC..."
                    )
                    self._initialized = False
                    os._exit(1)
                else:
                    logger.info(f"Algo trading: {'enabled' if info and info.trade_allowed else 'unknown'}")
            else:
                error_code, error_msg = mt5.last_error()
                self._ipc_failures += 1
                logger.error(
                    f"MT5 initialization failed ({self._ipc_failures}/{MAX_IPC_RETRIES}): "
                    f"{error_msg} ({error_code})"
                )

                if self._ipc_failures >= MAX_IPC_RETRIES:
                    logger.critical(
                        f"MT5 IPC failed {MAX_IPC_RETRIES} times — "
                        "exiting server for fresh wineserver restart..."
                    )
                    # os._exit bypasses try/except — supervisor restarts
                    # both the server and MT5 (autorestart=true)
                    os._exit(1)
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
