import hashlib
import hmac
import json
import time
from typing import Any

from candidate_comms.integrations.messaging.simulator.gateway import SIGNATURE_HEADER


def signed_webhook(
    payload: dict[str, Any], *, secret: str, timestamp: int | None = None
) -> tuple[bytes, dict[str, str]]:
    """Body and headers exactly as the provider simulator sends a webhook."""
    body = json.dumps(payload).encode()
    t = str(timestamp if timestamp is not None else int(time.time()))
    signature = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return body, {SIGNATURE_HEADER: f"t={t},v1={signature}"}
