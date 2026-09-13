from app.config.base import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)7s %(module)20s:%(lineno)4d - %(message)s",
            "datefmt": "%d-%m-%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "info.log"),
            "formatter": "verbose",
            "encoding": "utf-8",
            "maxBytes": 1024 * 1024,
            "backupCount": 3,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
}
