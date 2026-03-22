"""Type stubs for system.perspective — auto-generated from api_db."""

from typing import Any, Callable, Optional

def sendMessage(messageType: str, payload: dict[str, Any], scope: str = "page", sessionId: str = None, pageId: str = None) -> None:
    """Sends a message to component message handlers within a session. Handlers execute asynchronously."""
    ...

def print(message: str, sessionId: str = None, pageId: str = None, destination: str = "client") -> None:
    """Prints message to browser console or gateway logs."""
    ...

def navigate(page: str, url: str = None, view: str = None, params: dict[str, Any] = None, sessionId: str = None, pageId: str = None) -> None:
    """Navigates a session to a specified view or page."""
    ...

def openPopup(id: str, view: str, params: dict[str, Any] = None, title: str = None, position: dict[str, Any] = None, showCloseIcon: bool = True, draggable: bool = True, modal: bool = False) -> None:
    """Opens a popup view over the current page."""
    ...

def closePopup(id: str, sessionId: str = None, pageId: str = None) -> None:
    """Closes a popup with the specified ID."""
    ...

def togglePopup(id: str, view: str, params: dict[str, Any] = None) -> None:
    """Opens a popup if closed, closes it if open."""
    ...

def getSessionInfo(sessionId: str = None, pageId: str = None) -> dict[str, Any]:
    """Returns information about a Perspective session."""
    ...

def getProjectInfo() -> dict[str, Any]:
    """Returns information about the current Perspective project."""
    ...

def openDock(id: str, sessionId: str = None, pageId: str = None) -> None:
    """Opens a docked view."""
    ...

def closeDock(id: str, sessionId: str = None, pageId: str = None) -> None:
    """Closes a docked view."""
    ...

def toggleDock(id: str) -> None:
    """Toggles a docked view open or closed."""
    ...

def refresh(sessionId: str = None, pageId: str = None) -> None:
    """Triggers a refresh of the page."""
    ...

def setTheme(name: str, sessionId: str = None, pageId: str = None) -> None:
    """Changes the theme in a page to the specified theme."""
    ...

def vibrate(duration: int = 100, sessionId: str = None) -> None:
    """Causes device running Perspective Mobile App to vibrate."""
    ...

def navigateForward(sessionId: str = None, pageId: str = None) -> None:
    """Navigate forward in session history (like browser forward button)."""
    ...

def navigateBack(sessionId: str = None, pageId: str = None) -> None:
    """Navigate back in session history (like browser back button)."""
    ...

def download(filename: str, data: str | bytes, contentType: str = "text/plain") -> None:
    """Triggers a download in the user's browser."""
    ...
