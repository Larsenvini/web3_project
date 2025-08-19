import logging, sys, structlog

def setup_logging(log_level: str = "INFO"):
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer() if not sys.stdout.isatty()
        else structlog.dev.ConsoleRenderer()
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True
    )

    logging.basicConfig(level=log_level)

def get_logger(name: str):
    return structlog.get_logger(name)