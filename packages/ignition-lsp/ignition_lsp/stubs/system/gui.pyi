"""Type stubs for system.gui — auto-generated from api_db."""

from typing import Any, Callable, Optional

def messageBox(message: str, title: str = "Information") -> None:
    """Displays an informational-style message popup box to the user."""
    ...

def warningBox(message: str, title: str = "Warning") -> None:
    """Displays a message to the user in a warning-style popup dialog."""
    ...

def errorBox(message: str, title: str = "Error") -> None:
    """Displays an error-style message box to the user."""
    ...

def confirm(message: str, title: str = "Confirm", allowCancel: bool = False) -> bool:
    """Displays a confirmation dialog box to the user with Yes and No buttons."""
    ...

def inputBox(message: str, defaultText: str = None) -> str:
    """Opens a popup input dialog box that shows a prompt message and allows the user to type in a string."""
    ...

def passwordBox(message: str, title: str = "Password", echoChar: str = "*") -> str:
    """Displays a password input dialog that masks the user's input."""
    ...

def chooseColor(initialColor: Any, title: str = "Choose Color") -> Any:
    """Prompts the user to pick a color using the default color-chooser dialog box."""
    ...

def color(red: int | str, green: int = None, blue: int = None, alpha: int = 255) -> Any:
    """Creates a new color object from RGB(A) values or by parsing a color string."""
    ...

def openDesktop(screen: int = None, handle: str = None, title: str = None, width: int = None, height: int = None, x: int = None, y: int = None, windows: list[str] = None) -> Any:
    """Creates an additional Desktop in a new frame."""
    ...

def closeDesktop(handle: str = None) -> None:
    """Closes an open desktop associated with the current client."""
    ...

def desktop(handle: str = None) -> DesktopHandle:
    """Allows you to invoke system.gui functions on a specific desktop."""
    ...

def getCurrentDesktop() -> str:
    """Returns the handle of the desktop that the current script is running in."""
    ...

def getDesktopHandles() -> list[str]:
    """Returns a list of all secondary desktop handles currently open in the client."""
    ...

def getWindow(windowPath: str) -> FPMIWindow:
    """Finds a reference to an open window with the given path."""
    ...

def findWindow(windowPath: str) -> list[FPMIWindow]:
    """Finds and returns a list of windows with the given path."""
    ...

def getWindowNames() -> list[str]:
    """Returns a list of the paths of all windows in the current project."""
    ...

def getOpenedWindows() -> Tuple[FPMIWindow]:
    """Finds all of the currently open windows and returns a tuple of references to them."""
    ...

def getOpenedWindowNames() -> Tuple[String]:
    """Finds all of the currently open windows, returning a tuple of their paths."""
    ...

def getParentWindow(event: EventObject) -> FPMIWindow:
    """Finds the parent window of a component that fired an event."""
    ...

def getSibling(event: EventObject, name: str) -> VisionComponent:
    """Given a component event object, looks up a sibling component."""
    ...

def getQuality(component: VisionComponent, propertyName: str) -> int:
    """Returns the data quality for the property of the given component."""
    ...

def transform(component: VisionComponent, newX: int = None, newY: int = None, newWidth: int = None, newHeight: int = None, duration: int = 0, framesPerSecond: int = 24, acceleration: int = 0, callback: Callable[..., Any] = None) -> None:
    """Sets a component's position and size at runtime, with optional animation."""
    ...

def convertPointToScreen(x: int, y: int, event: EventObject) -> Tuple:
    """Converts coordinates relative to a component to screen coordinates."""
    ...

def createPopupMenu(itemNames: list[str], itemFunctions: list[Callable[..., Any]]) -> JPopupMenu:
    """Creates a popup menu with string entries and function click handlers."""
    ...

def getScreenIndex() -> int:
    """Returns the index of the screen that the client is currently on."""
    ...

def setScreenIndex(index: int) -> None:
    """Moves the client to a specific monitor by screen index."""
    ...

def getScreens() -> Any:
    """Returns a list of all monitors on the computer the client is running on."""
    ...

def isTouchscreenModeEnabled() -> bool:
    """Checks whether the running client's Touch Screen mode is enabled."""
    ...

def setTouchscreenModeEnabled(enabled: bool) -> None:
    """Enables or disables Touch Screen mode on the running client."""
    ...

def showNumericKeypad(initialValue: Number = None, fontSize: int = None, usePasswordMode: bool = False) -> Number:
    """Displays a modal on-screen numeric keypad for mouse or touchscreen input."""
    ...

def showTouchscreenKeyboard(initialText: str = None, fontSize: int = None, passwordMode: bool = False) -> str:
    """Displays a modal on-screen keyboard for mouse or touchscreen text entry."""
    ...

def openDiagnostics() -> None:
    """Opens the Client runtime Diagnostics window."""
    ...
