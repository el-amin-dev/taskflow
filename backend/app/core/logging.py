import json
import logging
import logging.config
import sys
from datetime import datetime , timezone
from app.core.config import Environment

class JsonFormatter (logging.Formatter):
    _RESERVED = frozenset(
        logging.LogRecord(
            "", 0, "", 0, "", None, None
        ).__dict__.keys()
    ) | {"message" , "asctime"}

    def format (self , record :logging.LogRecord) -> str:
        payload: dict [str,object] = {
            "ts":datetime.fromtimestamp(record.created,tz=timezone.utc).isoformat(),
            "level" : record.levelname,
            "logger" : record.name,
            "msg" : record.getMessage(),
        }
        if record.exc_info:
            payload['exc'] = self.formatException(record.exc_info)

        for key , value in record.__dict__.items():
            if key not in self._RESERVED:
                payload[key] = value
        return json.dumps(payload,default=str)

_COLORS = {
    "DEBUG": "\033[36m",  
    "INFO": "\033[32m",    
    "WARNING": "\033[33m",  
    "ERROR": "\033[31m", 
    "CRITICAL": "\033[35m",  
}
_RESET = "\033[0m"

class DevFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        return f"{color}{ts} {record.levelname:<8}{_RESET} {record.name} — {record.getMessage()}"




def setup_logging(environment: Environment, level: str = "INFO") -> None:

    formatter_name = "dev" if environment == Environment.DEV else "json"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": JsonFormatter},
                "dev": {"()": DevFormatter},
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": formatter_name,
                },
            },
            "root": {"level": level, "handlers": ["stdout"]},
            "loggers": {

                "uvicorn": {"level": level, "handlers": ["stdout"], "propagate": False},
                "uvicorn.error": {"level": level, "handlers": ["stdout"], "propagate": False},
                "uvicorn.access": {"level": level, "handlers": ["stdout"], "propagate": False},
            },
        }
    )