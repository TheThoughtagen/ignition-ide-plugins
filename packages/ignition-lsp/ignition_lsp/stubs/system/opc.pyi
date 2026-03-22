"""Type stubs for system.opc — auto-generated from api_db."""

from typing import Any, Callable, Optional

def browse(opcServer: str = None, device: str = None, folderPath: str = None, opcItemPath: str = None) -> list[OPCBrowseTag]:
    """Browses OPC servers in the runtime, returning a list of tags."""
    ...

def browseServer(opcServer: str, nodeId: str) -> list[OPCBrowseElement]:
    """Browses a single level of an OPC server, returning child nodes for the given node ID."""
    ...

def browseSimple(opcServer: str, device: str, folderPath: str, opcItemPath: str) -> list[OPCBrowseTag]:
    """Browses OPC servers in the runtime, returning a list of tags. All parameters are required but can be None."""
    ...

def getServers(includeDisabled: bool = False) -> list[str]:
    """Returns a list of configured OPC server connection names."""
    ...

def getServerState(opcServer: str) -> str:
    """Returns the current state of the given OPC server connection."""
    ...

def isServerEnabled(serverName: str) -> bool:
    """Checks if an OPC server connection is enabled or disabled."""
    ...

def readValue(opcServer: str, itemPath: str) -> Any:
    """Reads a single value directly from an OPC server connection."""
    ...

def readValues(opcServer: str, itemPaths: list[str]) -> list[Any]:
    """Reads multiple values directly from an OPC server connection in bulk."""
    ...

def setServerEnabled(serverName: str, enabled: bool) -> None:
    """Enables or disables an OPC server connection."""
    ...

def writeValue(opcServer: str, itemPath: str, value: Any) -> Quality:
    """Writes a value directly through an OPC server connection synchronously."""
    ...

def writeValues(opcServer: str, itemPaths: list[str], values: list[Any]) -> list[Quality]:
    """Writes multiple values directly through an OPC server connection in bulk."""
    ...
