"""Type stubs for system.file — auto-generated from api_db."""

from typing import Any, Callable, Optional

def fileExists(filepath: str) -> bool:
    """Checks if a file or folder exists at the given path."""
    ...

def getTempFile(extension: str) -> str:
    """Creates a new temporary file with the given extension and returns the path."""
    ...

def openFile(extension: str = None, defaultLocation: str = None) -> str:
    """Shows an 'Open File' dialog, prompting the user to choose a file to open."""
    ...

def openFiles(extension: str = None, defaultLocation: str = None) -> list[str]:
    """Shows an 'Open File' dialog allowing the user to select one or more files."""
    ...

def readFileAsBytes(filepath: str) -> bytes:
    """Reads the entire file at the given path and returns it as a byte array."""
    ...

def readFileAsString(filepath: str, encoding: str = None) -> str:
    """Reads the entire file at the given path and returns it as a string."""
    ...

def saveFile(filename: str, extension: str = None, typeDesc: str = None) -> str:
    """Shows a 'Save As' dialog, prompting the user to choose a save location and filename."""
    ...

def writeFile(filepath: str, data: str | bytes, append: bool = False, encoding: str = "UTF-8") -> None:
    """Writes the given data to the file at the specified path."""
    ...
