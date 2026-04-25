"""Async Python SDK for the dessmonitor / shinemonitor API.

In-tree subpackage of the Home Assistant integration. Public surface is intentionally
small — instantiate :class:`DessmonitorClient` and reach endpoints via its resource
attributes (``client.devices``, ``client.auth``, …).
"""
from __future__ import annotations

from .client import DessmonitorClient
from .errors import (
    ApiError,
    AuthError,
    DessmonitorError,
    RateLimitError,
    TransportError,
)
from .http import HttpClient
from .models import (
    Auth,
    AuthDict,
    CollectorListResponse,
    Credentials,
    CtrlField,
    CtrlFieldOption,
    CtrlFieldsResponse,
    CtrlValueResponse,
    Datalogger,
    DeviceDict,
    DeviceIdentity,
    DirectCommandResponse,
    EnergyFlowResponse,
    Envelope,
    FieldsResponse,
    HistoricalDataResponse,
    LastDataResponse,
    Param,
    ParsResponse,
)
from .session import Session
from .storage import InMemoryTokenStorage, TokenStorage
from .streaming import DeviceStream, StreamFrame

__all__ = [
    "ApiError",
    "Auth",
    "AuthDict",
    "AuthError",
    "CollectorListResponse",
    "Credentials",
    "CtrlField",
    "CtrlFieldOption",
    "CtrlFieldsResponse",
    "CtrlValueResponse",
    "Datalogger",
    "DessmonitorClient",
    "DessmonitorError",
    "DeviceDict",
    "DeviceIdentity",
    "DeviceStream",
    "DirectCommandResponse",
    "EnergyFlowResponse",
    "Envelope",
    "FieldsResponse",
    "HistoricalDataResponse",
    "HttpClient",
    "InMemoryTokenStorage",
    "LastDataResponse",
    "Param",
    "ParsResponse",
    "RateLimitError",
    "Session",
    "StreamFrame",
    "TokenStorage",
    "TransportError",
]
