"""Type stubs for system.db — auto-generated from api_db."""

from typing import Any, Callable, Optional

def runQuery(query: str, database: str = None, tx: str = None) -> Any:
    """Executes a SQL SELECT query and returns results as a Dataset."""
    ...

def runPrepQuery(query: str, args: list[Any], database: str = None, tx: str = None) -> Any:
    """Executes a prepared statement with parameters. Prevents SQL injection."""
    ...

def runUpdateQuery(query: str, database: str = None, tx: str = None, getKey: bool = False, skipAudit: bool = False) -> int:
    """Executes UPDATE, INSERT, or DELETE queries."""
    ...

def runPrepUpdate(query: str, args: list[Any], database: str = None, getKey: bool = False) -> int:
    """Executes prepared UPDATE/INSERT/DELETE with parameters."""
    ...

def beginTransaction(database: str = None, timeout: int = 5000) -> str:
    """Begins a new database transaction. Returns transaction ID for use in queries."""
    ...

def commitTransaction(tx: str) -> None:
    """Commits a transaction, making all changes permanent."""
    ...

def rollbackTransaction(tx: str) -> None:
    """Rolls back a transaction, discarding all changes."""
    ...

def closeTransaction(tx: str) -> None:
    """Closes a transaction, releasing database resources."""
    ...

def createSProcCall(procedureName: str, database: str = None) -> SProcCall:
    """Creates a stored procedure call object that can be configured and executed."""
    ...

def execSProcCall(callObject: SProcCall) -> Any:
    """Executes a stored procedure call."""
    ...
