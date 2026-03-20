"""Type stubs for system.util — auto-generated from api_db."""

from typing import Any, Callable, Optional

def getLogger(name: str) -> Logger:
    """Returns a Logger object for the specified name. Use for structured logging."""
    ...

def jsonDecode(jsonString: str) -> Any:
    """Parses a JSON string into a Python object."""
    ...

def jsonEncode(pyObject: Any, indentFactor: int = 4) -> str:
    """Encodes a Python object as a JSON string."""
    ...

def sendMessage(project: str, messageHandler: str, payload: dict[str, Any], scope: str = "G") -> list[Any]:
    """Sends a message to a project's message handler."""
    ...

def invokeAsynchronous(function: Callable[..., Any], args: list[Any] = None, kwargs: dict[str, Any] = None, description: str = None) -> Thread:
    """Invokes a function asynchronously on a separate thread."""
    ...

def invokeLater(function: Callable[..., Any], delay: int = 0) -> None:
    """Invokes a function after a delay on the GUI thread (Vision/Perspective)."""
    ...

def execute(commands: list[str], args: list[str] = None, timeoutSec: int = 60) -> str:
    """Executes a system command and returns output."""
    ...

def getSystemFlags() -> int:
    """Returns system flags indicating various states (mobile, workstation, etc.)."""
    ...

def getGlobals() -> dict[str, Any]:
    """Returns the global scripting namespace dictionary."""
    ...

def setGlobals(dictionary: dict[str, Any]) -> None:
    """Sets global scripting variables from a dictionary."""
    ...
