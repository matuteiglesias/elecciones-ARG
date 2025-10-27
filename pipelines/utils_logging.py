# pipelines/utils_logging.py
import logging, sys

def get_logger(name: str = None, level: int = logging.DEBUG) -> logging.Logger:
    """
    Return a logger with a single stdout handler; safe to call multiple times.
    """
    log = logging.getLogger(name) if name else logging.getLogger()
    log.setLevel(level)

    # Add only one StreamHandler to this logger
    if not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
        h = logging.StreamHandler(stream=sys.stdout)
        h.setLevel(level)
        h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        log.addHandler(h)

    # Avoid double-propagation to root (prevents duplicate lines)
    log.propagate = False
    return log


import logging
import sys

def setup_logging(level=logging.DEBUG):
    # Single place to configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # ensure we override any prior config
    )
    logger = logging.getLogger(__name__)
    logger.debug("Logging configured")
    return logger

if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Logging initialized at level %s", logging.getLevelName(logger.level))
    run(cfg)
