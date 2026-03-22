"""Type stubs for system.dataset — auto-generated from api_db."""

from typing import Any, Callable, Optional

def addColumn(dataset: Any, colIndex: int = None, col: list[Any], colName: str, colType: Type) -> Any:
    """Returns a new dataset with a new column added or inserted."""
    ...

def addRow(dataset: Any, rowIndex: int = None, row: list[Any]) -> Any:
    """Returns a new dataset with a new row added or inserted."""
    ...

def addRows(dataset: Any, rowIndex: int = None, rows: list[list[Any]]) -> Any:
    """Returns a new dataset with multiple new rows added or inserted."""
    ...

def appendDataset(dataset1: Any, dataset2: Any) -> Any:
    """Returns a new dataset with the second dataset's rows appended to the first."""
    ...

def clearDataset(dataset: Any) -> Any:
    """Returns a new dataset with the same columns but all rows removed."""
    ...

def dataSetToHTML(showHeaders: bool, dataset: Any, title: str) -> str:
    """Formats the contents of a dataset as an HTML page and returns the result as a string."""
    ...

def deleteRow(dataset: Any, rowIndex: int) -> Any:
    """Returns a new dataset with a single row removed."""
    ...

def deleteRows(dataset: Any, rowIndices: list[int]) -> Any:
    """Returns a new dataset with one or more rows removed."""
    ...

def exportCSV(filename: str, showHeaders: bool, dataset: Any, forceQualifiedPath: bool = True) -> str:
    """Exports the contents of a dataset as a CSV file, prompting the user to save."""
    ...

def exportExcel(filename: str, showHeaders: bool, dataset: list[Any], nullsEmpty: bool = False) -> str:
    """Exports the contents of a dataset as an Excel spreadsheet, prompting the user to save."""
    ...

def exportHTML(filename: str, showHeaders: bool, dataset: Any, title: str) -> str:
    """Exports the contents of a dataset to an HTML page, prompting the user to save."""
    ...

def filterColumns(dataset: Any, columns: list[int] | List[String]) -> Any:
    """Returns a new dataset containing only the specified columns."""
    ...

def formatDates(dataset: Any, dateFormat: str, locale: str = None) -> Any:
    """Returns a new dataset with Date columns converted to formatted strings."""
    ...

def fromCSV(csv: str) -> Any:
    """Converts a dataset stored in Ignition's CSV format string to a Dataset."""
    ...

def getColumnHeaders(dataset: Any) -> list[str]:
    """Returns the column headers of a dataset as a Python list."""
    ...

def setValue(dataset: Any, rowIndex: int, colIndex: int | str, value: Any) -> Any:
    """Returns a new dataset with one cell value changed."""
    ...

def sort(dataset: Any, keyColumn: int | str, ascending: bool = True, naturalOrdering: bool = True) -> Any:
    """Sorts a dataset by a specified column and returns the sorted result."""
    ...

def toCSV(dataset: Any, showHeaders: bool = True, forExport: bool = False, localized: bool = False) -> str:
    """Formats the contents of a dataset as a CSV string."""
    ...

def toDataSet(headers: list[str], data: list[list[Any]] = None) -> Any:
    """Creates a new Dataset from column headers and row data, or converts a PyDataset to a Dataset."""
    ...

def toExcel(showHeaders: bool, dataset: list[Any], nullsEmpty: bool = False, sheetNames: list[str] = None) -> bytes:
    """Formats one or more datasets as an Excel spreadsheet and returns the result as a byte array."""
    ...

def toPyDataSet(dataset: Any) -> PyDataset:
    """Converts a Dataset to a PyDataset for more Pythonic access (iteration, indexing)."""
    ...

def updateRow(dataset: Any, rowIndex: int, changes: Dictionary[String, Any]) -> Any:
    """Returns a new dataset with one row altered based on the provided column-value mappings."""
    ...
