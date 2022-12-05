__all__ = [
    "MonoFormatError",
    "StopError",
    "NoFormatterFound",
]


class MonoFormatError(Exception):
    """Base class for exceptions in this module."""


class StopError(MonoFormatError):
    """
    Exception raised when one or more formatters failed to stop
    """

    def __init__(self, message, sub_exceptions):
        self.sub_exceptions = sub_exceptions
        super().__init__(message)


class NoFormatterFound(MonoFormatError):
    """
    Exception raised when no formatter is found for a file
    """
