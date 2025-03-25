import datetime
import os
from logging import (DEBUG, INFO, FileHandler, Formatter, Logger, StreamHandler,
                     setLoggerClass)
from logging.handlers import RotatingFileHandler
from typing import Optional

import pytz


class CustomLogger(Logger):
    """Custom logger with console and file output, and formatted messages."""

    def __init__(
        self,
        name: str,
        level: int = INFO,
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
        max_log_size: int = 10 * 1024 * 1024,  # Default: 10MB
        backup_count: int = 5,
    ):  # Default: 5 backups
        """
        Initializes a custom logger with configurable handlers.

        :param name: Name of the logger.
        :param level: Logging level (e.g., INFO, DEBUG, ERROR).
        :param log_to_file: Whether to log to a file (default: False).
        :param log_file_path: Path to the log file (if logging to a file).
        :param max_log_size: Maximum size of the log file before rotation (default: 10MB).
        :param backup_count: Number of backup log files to keep (default: 5).
        """

        super().__init__(name, level)
        timezone = pytz.timezone("Asia/Tehran")

        # Custom formatter with timezone conversion

        class TZFormatter(Formatter):
            """override logging.Formatter to use an aware datetime object"""

            def converter(self, timestamp):
                dt = datetime.datetime.fromtimestamp(timestamp)
                tzinfo = pytz.timezone("Asia/Tehran")
                return tzinfo.localize(dt)

            def formatTime(self, record, datefmt=None):
                dt = self.converter(record.created)
                if datefmt:
                    s = dt.strftime(datefmt)
                else:
                    try:
                        s = dt.isoformat(timespec="milliseconds")
                    except TypeError:
                        s = dt.isoformat()
                return s

        # Formatter for log messages
        formatter = TZFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Console handler for standard output
        console_handler = StreamHandler()
        console_handler.setFormatter(formatter)

        # Add console handler if not already present
        if not self.hasHandlers():
            self.addHandler(console_handler)

        # File handler setup (if enabled)
        if log_to_file and log_file_path:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

            # Use RotatingFileHandler to limit file size and rotate logs
            file_handler = RotatingFileHandler(
                log_file_path, maxBytes=max_log_size, backupCount=backup_count
            )
            file_handler.setFormatter(formatter)

            self.addHandler(file_handler)

        # Set the default logging level (INFO, DEBUG, etc.)
        self.setLevel(level)

        # Avoid duplicate handlers (handled by `hasHandlers()` check above)

    def log_to_console(self, level: int = INFO) -> None:
        """Logs a message to the console."""
        self.setLevel(level)
        for handler in self.handlers:
            if isinstance(handler, StreamHandler):
                handler.setLevel(level)

    def log_to_file(self, level: int = INFO) -> None:
        """Logs a message to the file."""
        self.setLevel(level)
        for handler in self.handlers:
            if isinstance(handler, FileHandler) or isinstance(
                handler, RotatingFileHandler
            ):
                handler.setLevel(level)


setLoggerClass(
    type(
        "MyCustomLogger",
        (CustomLogger,),
        {
            "__init__": lambda self, name: CustomLogger.__init__(
                self,
                name,
                level=DEBUG,
                backup_count=3,
                max_log_size=1024 * 1024,
                log_to_file=True,
                log_file_path=f"logs/{name}.log",
            )
        },
    )
)
