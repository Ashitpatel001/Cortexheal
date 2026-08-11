import logging
import json
import sys
from datetime import datetime
from cortexheal.config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "environment": settings.ENVIRONMENT,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger("cortexheal")
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
    logger.setLevel(level)
    
    # Also capture uvicorn/fastapi logs if needed
    logging.getLogger("uvicorn.access").handlers = logger.handlers
    
    return logger
