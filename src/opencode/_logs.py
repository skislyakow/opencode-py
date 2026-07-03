from __future__ import annotations

import logging
import os

logger = logging.getLogger("opencode")


def setup_logging() -> None:
    env = os.environ.get("OPENCODE_LOG")
    if env == "debug":
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.setLevel(logging.DEBUG)
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.DEBUG)
    elif env == "info":
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.setLevel(logging.INFO)
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.INFO)
