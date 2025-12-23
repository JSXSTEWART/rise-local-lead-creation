"""
A lightweight stand-in for the ``dotenv`` package used in this project.

The real `python-dotenv` library is used in production to load
environment variables from a .env file into ``os.environ``. In testing
environments where external dependencies cannot be installed, this
module provides a no-op ``load_dotenv`` function so that ``import
dotenv`` succeeds without raising ``ModuleNotFoundError``.

Usage:

    from dotenv import load_dotenv
    load_dotenv()  # does nothing by default

If you need to simulate loading variables from a file, you can pass a
custom dictionary of key-value pairs via the ``override`` parameter.
This will update ``os.environ`` accordingly.
"""

from typing import Optional, Dict
import os


def load_dotenv(path: Optional[str] = None, *, override: Optional[Dict[str, str]] = None, **kwargs) -> None:
    """Load environment variables from a .env file or a provided mapping.

    This is a simplified implementation intended for use in test
    environments where the external ``python-dotenv`` package is not
    available. It accepts an optional ``override`` dictionary which will
    be merged into ``os.environ``. The ``path`` argument is accepted for
    API compatibility but ignored.

    Args:
        path: Optional path to a .env file (ignored).
        override: Optional mapping of environment variables to set.
        **kwargs: Additional keyword arguments for compatibility; ignored.

    Returns:
        None
    """
    if override:
        for key, value in override.items():
            # Only set variables that are not already present to avoid
            # overwriting intentionally provided values.
            os.environ.setdefault(key, value)
