from __future__ import annotations

import logging


def configure_logging() -> None:
    """Configure metadata-only application logging.

    Request bodies, prompts, profiles, chats, and credentials are intentionally
    excluded from the default log format.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

