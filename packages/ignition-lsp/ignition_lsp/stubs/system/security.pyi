"""Type stubs for system.security — auto-generated from api_db."""

from typing import Any, Callable, Optional

def getRoles() -> Tuple[String]:
    """Returns the roles assigned to the currently logged in user as a tuple of strings."""
    ...

def getUsername() -> str:
    """Returns the username of the currently logged in user."""
    ...

def getUserRoles(username: str, password: str, authProfile: str = None, timeout: int = 60000) -> Tuple[String]:
    """Fetches the roles for a specified user from the Gateway by validating credentials."""
    ...

def isScreenLocked() -> bool:
    """Returns whether or not the screen is currently in lock-screen mode."""
    ...

def lockScreen(obscure: bool = None) -> None:
    """Puts the running Vision Client into lock-screen mode."""
    ...

def logout() -> None:
    """Logs out the current user and returns the client to the login screen."""
    ...

def switchUser(username: str, password: str, event: EventObject = None, hideError: bool = False) -> bool:
    """Attempts to switch the current user on the fly without fully logging out."""
    ...

def unlockScreen() -> None:
    """Unlocks the Vision Client if it is currently in lock-screen mode."""
    ...

def validateUser(username: str, password: str, authProfile: str = None, timeout: int = 60000) -> bool:
    """Tests credentials against an authentication profile to check if they are valid."""
    ...
