
import logging


def configure_logging() -> None:
    """Configure basic logging if not already configured.

    - Sets root logger to INFO with a simple format
    - Keeps uvicorn access logs at INFO for consistency
    """
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
