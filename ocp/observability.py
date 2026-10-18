"""Structured log lines: `log_event("checkout.failed", order="FW-1", reason="sold_out")`."""

import logging

logger = logging.getLogger("ocp")


def _fmt(value):
    text = str(value)
    return f'"{text}"' if " " in text else text


def log_event(name, level=logging.INFO, **fields):
    parts = [f"event={name}"] + [f"{key}={_fmt(value)}" for key, value in fields.items()]
    logger.log(level, " ".join(parts))
