from logging import getLogger
from traceback import format_exc

logger = getLogger("errors")


class ErrorHandler:
    @staticmethod
    def handle(exception: Exception):
        """Handles exceptions by logging them with traceback details.

        Args:
            exception (Exception): The exception to handle.
            raise_exception (bool): Whether to re-raise the exception after logging.
        """
        raise exception
        # return (
        #     f"Exception: {type(Exception).__name__}\n"
        #     f"Stack trace:\n{format_exc()}"
        # )
        # logger.error("An error occurred: %s", str(exception))
        # logger.debug("Stack trace:\n%s", format_exc())
