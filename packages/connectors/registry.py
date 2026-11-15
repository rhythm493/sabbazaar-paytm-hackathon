from __future__ import annotations

from contracts.channels import ChannelConnector


class ConnectorRegistry:
    """Maps channel name -> connector. Only explicitly registered channels are 'connected'."""

    def __init__(self) -> None:
        self._by_channel: dict[str, ChannelConnector] = {}

    def register(self, connector: ChannelConnector) -> None:
        self._by_channel[connector.channel] = connector

    def get(self, channel: str) -> ChannelConnector:
        return self._by_channel[channel]

    def channels(self) -> list[str]:
        return list(self._by_channel)

    def simulated_channels(self) -> list[str]:
        return [c for c, conn in self._by_channel.items() if conn.simulated]
