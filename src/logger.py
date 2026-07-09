"""Central logging: one rotating file per area plus console."""
import logging
import os
from logging.handlers import RotatingFileHandler

_loggers = {}


def get_logger(name, log_dir="logs"):
    if name in _loggers:
        return _loggers[name]
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = RotatingFileHandler(os.path.join(log_dir, f"{name}.log"),
                             maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)
    _loggers[name] = logger
    return logger
