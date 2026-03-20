"""Type stubs for system.tag — auto-generated from api_db."""

from typing import Any, Callable, Optional

def readBlocking(tagPaths: str | list[str], timeout: int = 45000) -> list[Any]:
    """Reads the value of tags at the given paths. Blocks until complete or timeout."""
    ...

def readAsync(tagPaths: list[str], callback: Callable[..., Any]) -> None:
    """Asynchronously reads tag values. Callback is invoked when complete."""
    ...

def writeBlocking(tagPaths: list[str], values: list[Any], timeout: int = 45000) -> list[Any]:
    """Writes values to tags at specified paths. Blocks until complete or timeout."""
    ...

def writeAsync(tagPaths: list[str], values: list[Any], callback: Callable[..., Any] = None) -> None:
    """Asynchronously writes values to tags. Non-blocking operation."""
    ...

def exists(tagPath: str) -> bool:
    """Checks whether a tag with the given path exists."""
    ...

def queryTagHistory(paths: list[str], startDate: Any, endDate: Any, returnSize: int = -1, aggregationMode: str = "Average") -> Any:
    """Issues a query to the Tag Historian. Returns historical data for specified tags."""
    ...

def browse(path: str, filter: dict[str, Any] = None) -> list[BrowseTag]:
    """Returns a list of nodes found at the specified path."""
    ...

def configure(basePath: str, tags: list[dict[str, Any]], collisionPolicy: str = "o") -> list[Any]:
    """Creates or modifies tags from Python dictionaries or JSON. Most flexible way to create tags programmatically."""
    ...

def getConfiguration(basePath: str, recursive: bool = False) -> list[dict[str, Any]]:
    """Retrieves tag configurations as Python dictionaries that can be modified and re-applied with configure()."""
    ...

def deleteTags(tagPaths: list[str]) -> list[Any]:
    """Deletes multiple tags or tag folders. Use with caution."""
    ...

def copy(tags: list[str], destination: str, collisionPolicy: str = "o") -> list[Any]:
    """Copies tags from one folder to another."""
    ...

def move(tags: list[str], destination: str, collisionPolicy: str = "a") -> list[Any]:
    """Moves tags or folders to a new destination."""
    ...

def rename(tagPath: str, newName: str, collisionPolicy: str = "a") -> Any:
    """Renames a single tag or folder."""
    ...

def exportTags(filePath: str, tagPaths: list[str], recursive: bool = True) -> None:
    """Exports tags to a JSON file on the local file system."""
    ...

def importTags(filePath: str, basePath: str, collisionPolicy: str = "o") -> list[Any]:
    """Imports tags from a JSON file into the tag system."""
    ...

def query(path: str, params: dict[str, Any] = None) -> Any:
    """Queries a Tag Provider to find tags matching specified criteria."""
    ...

def browseHistoricalTags(path: str) -> Any:
    """Browses for historical tags at the provided historical path."""
    ...

def queryTagCalculations(paths: list[str], calculations: list[str], startDate: Any, endDate: Any) -> Any:
    """Queries various calculations (aggregations) for tags over a time range."""
    ...

def storeTagHistory(historicalProvider: str, tagProvider: str, paths: list[str], values: list[Any], qualities: list[Any], timestamps: list[Any]) -> list[Any]:
    """Inserts data into the tag history system. Allows storing tag history via scripting."""
    ...

def requestGroupExecution(provider: str, tagGroup: str) -> None:
    """Sends a request to the specified tag group to execute immediately."""
    ...
