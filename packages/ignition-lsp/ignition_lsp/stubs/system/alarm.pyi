"""Type stubs for system.alarm — auto-generated from api_db."""

from typing import Any, Callable, Optional

def acknowledge(alarmIds: list[str], notes: str = None, username: str = None) -> list[str]:
    """Acknowledges any number of alarms, specified by their event IDs."""
    ...

def cancel(alarmIds: list[str]) -> None:
    """Cancels any number of alarm notification pipelines, specified by their event IDs."""
    ...

def createRoster(name: str, description: str) -> None:
    """Creates a new alarm notification roster."""
    ...

def getRosters() -> Dictionary[String, List[String]]:
    """Returns a mapping of roster names to lists of usernames contained in each roster."""
    ...

def getShelvedPaths() -> list[ShelvedPath]:
    """Returns a list of ShelvedPath objects representing all currently shelved alarms."""
    ...

def listPipelines(projectName: str = "alarm-pipelines") -> list[str]:
    """Returns a list of the available alarm notification pipelines in a project."""
    ...

def queryJournal(startDate: Any = None, endDate: Any = None, journalName: str = None, priority: list[int | str] = None, state: list[int | str] = None, path: list[str] = None, source: list[str] = None, displaypath: list[str] = None, all_properties: list[Tuple[String, String, Any]] = None, any_properties: list[Tuple[String, String, Any]] = None, defined: list[str] = None, includeData: bool = None, includeSystem: bool = None, includeShelved: bool = False, isSystem: bool = None, provider: list[str] = None) -> AlarmQueryResult:
    """Queries the alarm journal for historical alarm events within a time range."""
    ...

def queryStatus(priority: list[int | str] = None, state: list[int | str] = None, path: list[str] = None, source: list[str] = None, displaypath: list[str] = None, all_properties: list[Tuple[String, String, Any]] = None, any_properties: list[Tuple[String, String, Any]] = None, defined: list[str] = None, includeShelved: bool = False, provider: list[str] = None) -> AlarmQueryResult:
    """Queries the current state of alarms, returning a filterable list of alarm events."""
    ...

def shelve(path: list[str], timeoutSeconds: int = None, timeoutMinutes: int = 15) -> None:
    """Shelves the specified alarms for the given duration, suppressing notifications."""
    ...

def unshelve(path: list[str]) -> None:
    """Unshelves alarms at the specified source paths, re-enabling notifications."""
    ...
