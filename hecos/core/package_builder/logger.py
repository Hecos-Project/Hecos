import os
import logging
from pathlib import Path

def get_builder_logger():
    logger = logging.getLogger("PackageBuilder")
    # Prevent duplicate handlers if module is reloaded
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        log_file = Path(r"C:\Hecos\hecos\logs\builder_logs.log")
        log_file.parent.mkdir(exist_ok=True, parents=True)
        fh = logging.FileHandler(str(log_file), encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [BUILDER] %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger

_log = get_builder_logger()

def info(msg):
    _log.info(msg)

def error(msg):
    _log.error(msg)
