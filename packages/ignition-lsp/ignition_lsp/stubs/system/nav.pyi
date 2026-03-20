"""Type stubs for system.nav — auto-generated from api_db."""

from typing import Any, Callable, Optional

def centerWindow(path: str) -> None:
    """Centers the given window on the screen."""
    ...

def closeParentWindow(event: EventObject) -> None:
    """Closes the parent window of the component that fired the given event."""
    ...

def closeWindow(path: str) -> None:
    """Closes the window with the given path."""
    ...

def desktop(handle: str = None) -> INavUtilities:
    """Returns a navigation proxy for a specific desktop, enabling multi-monitor window management."""
    ...

def getCurrentWindow() -> str:
    """Returns the path of the currently displayed main-screen window."""
    ...

def goBack() -> None:
    """Navigates back to the previous main-screen window in the navigation history."""
    ...

def goForward() -> None:
    """Navigates forward to the next main-screen window after a goBack() call."""
    ...

def goHome() -> None:
    """Navigates to the configured home window using the Typical Navigation Strategy."""
    ...

def openWindow(path: str, params: Dictionary[String, Any] = None) -> Window:
    """Opens the window at the given path, or brings it to front if already open."""
    ...

def openWindowInstance(path: str, params: Dictionary[String, Any] = None) -> Window:
    """Opens a new window instance even if the window is already open."""
    ...

def swapTo(path: str, params: Dictionary[String, Any] = None) -> Window:
    """Swaps from the current main-screen window to the specified window."""
    ...

def swapWindow(swapFromPath: str | EventObject, swapToPath: str, params: Dictionary[String, Any] = None) -> Window:
    """Closes one window and opens another in a single swap operation."""
    ...
