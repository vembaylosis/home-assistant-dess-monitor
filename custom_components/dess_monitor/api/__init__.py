"""Domain logic complementing the low-level :mod:`custom_components.dess_monitor.sdk`.

Submodules:
* :mod:`api.protocols` — pluggable inverter protocol adapters (Axpert, PI18, ...).
* :mod:`api.transports` — byte-level transports for direct commands.
* :mod:`api.direct_service` — orchestration tying a transport to a protocol.
* :mod:`api.helpers`, :mod:`api.resolvers` — cloud-payload helpers.

Direct imports from this package's top level have been removed; import from
the relevant submodule instead.
"""
