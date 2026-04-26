"""Generic helpers for turning raw inverter replies into dicts."""
from __future__ import annotations

from typing import Any

from .base import Field, ResponseSchema


def strip_frame(raw: bytes) -> bytes:
    """Drop the protocol envelope (leading ``(`` or ``^Dnnn``, trailing CR + CRC).

    Both Voltronic Axpert and PI18 wrap the payload between a 1-byte (or
    4-byte) header and a 2-byte CRC followed by ``\\r``. The CRC is *not*
    re-validated here: the cloud relay strips/replaces it inconsistently
    across devcodes, and a strict check would mean false negatives in
    production. Transports that talk to the device directly should validate
    the CRC themselves before handing bytes off to ``Protocol.decode``.
    """
    if not raw:
        return raw
    payload = raw
    # Trim trailing CR (and anything after, e.g. when the cloud appends a NUL).
    cr = payload.find(b"\r")
    if cr != -1:
        payload = payload[:cr]
    # Strip the trailing 2-byte CRC if it is present.
    if len(payload) >= 2:
        payload = payload[:-2]
    # Strip the Axpert leading '(' header. PI18 uses a ``^D<len>`` header.
    if payload.startswith(b"("):
        payload = payload[1:]
    elif payload.startswith(b"^D") and len(payload) >= 5:
        payload = payload[5:]
    return payload


def decode_token(field: Field, token: str) -> Any:
    if field.enum is not None:
        try:
            return field.enum(token).name
        except ValueError:
            return token
    if field.transform is not None:
        return field.transform(token)
    return token


def parse_positional(payload: str, schema: ResponseSchema) -> dict[str, Any]:
    """Split ``payload`` on whitespace and zip with ``schema.fields``.

    Tokens past the schema length are ignored; fields without a token are
    omitted from the result. Each token is run through :func:`decode_token`
    so enum codes are normalised to their ``.name`` strings.
    """
    tokens = payload.split()
    result: dict[str, Any] = {}
    for field, token in zip(schema.fields, tokens):
        result[field.name] = decode_token(field, token)
    return result


def is_nak(payload: str) -> bool:
    return payload.startswith("NAK") or "NAK" in payload
