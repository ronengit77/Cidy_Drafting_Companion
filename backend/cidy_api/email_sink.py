from __future__ import annotations

import logging

from cidy_api.config import get_settings

logger = logging.getLogger("cidy_api.email")


def send_magic_link(email: str, link: str) -> None:
    if get_settings().dev_mode:
        logger.info("DEV magic link for %s: %s", email, link)
        return
    raise NotImplementedError("SES email delivery is implemented in Phase 2B")
