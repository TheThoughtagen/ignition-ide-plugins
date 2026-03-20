"""Type stubs for system.date — auto-generated from api_db."""

from typing import Any, Callable, Optional

def now() -> Any:
    """Returns the current date and time."""
    ...

def parse(dateString: str, formatString: str = "yyyy-MM-dd HH:mm:ss", locale: str = None) -> Any:
    """Parses a string into a Date using the given format pattern."""
    ...

def format(date: Any, formatString: str = "yyyy-MM-dd HH:mm:ss", locale: str = None) -> str:
    """Formats a Date as a string using the given format pattern."""
    ...

def midnight(date: Any) -> Any:
    """Returns a copy of the date with the time set to midnight (00:00:00)."""
    ...

def setTime(date: Any, hour: int, minute: int, second: int) -> Any:
    """Returns a copy of the date with the time fields set to the given values."""
    ...

def addHours(date: Any, hours: int) -> Any:
    """Adds (or subtracts) hours to a date."""
    ...

def addMinutes(date: Any, minutes: int) -> Any:
    """Adds (or subtracts) minutes to a date."""
    ...

def addSeconds(date: Any, seconds: int) -> Any:
    """Adds (or subtracts) seconds to a date."""
    ...

def addMillis(date: Any, millis: int) -> Any:
    """Adds (or subtracts) milliseconds to a date."""
    ...

def addDays(date: Any, days: int) -> Any:
    """Adds (or subtracts) days to a date."""
    ...

def addWeeks(date: Any, weeks: int) -> Any:
    """Adds (or subtracts) weeks to a date."""
    ...

def addMonths(date: Any, months: int) -> Any:
    """Adds (or subtracts) months to a date."""
    ...

def addYears(date: Any, years: int) -> Any:
    """Adds (or subtracts) years to a date."""
    ...

def getHour12(date: Any) -> int:
    """Returns the hour (12-hour clock) from the given date."""
    ...

def getHour24(date: Any) -> int:
    """Returns the hour (24-hour clock) from the given date."""
    ...

def getMinute(date: Any) -> int:
    """Returns the minute from the given date."""
    ...

def getSecond(date: Any) -> int:
    """Returns the second from the given date."""
    ...

def getMillis(date: Any) -> int:
    """Returns the millisecond portion from the given date."""
    ...

def getYear(date: Any) -> int:
    """Returns the year from the given date."""
    ...

def getMonth(date: Any) -> int:
    """Returns the month from the given date. January is 0."""
    ...

def getDayOfMonth(date: Any) -> int:
    """Returns the day of the month from the given date."""
    ...

def getDayOfWeek(date: Any) -> int:
    """Returns the day of the week from the given date. Sunday is 1."""
    ...

def getDayOfYear(date: Any) -> int:
    """Returns the day of the year from the given date."""
    ...

def getAMorPM(date: Any) -> int:
    """Returns 0 for AM, 1 for PM for the given date."""
    ...

def getDate(year: int, month: int, day: int) -> Any:
    """Creates a new Date from year, month, and day with time at midnight."""
    ...

def getTimezone() -> str:
    """Returns the ID of the current timezone."""
    ...

def getTimezoneOffset(date: Any = None) -> float:
    """Returns the timezone offset from UTC in hours, accounting for DST."""
    ...

def getTimezoneRawOffset() -> float:
    """Returns the raw timezone offset from UTC in hours, ignoring DST."""
    ...

def hoursBetween(date1: Any, date2: Any) -> int:
    """Returns the number of whole hours between two dates."""
    ...

def minutesBetween(date1: Any, date2: Any) -> int:
    """Returns the number of whole minutes between two dates."""
    ...

def secondsBetween(date1: Any, date2: Any) -> int:
    """Returns the number of whole seconds between two dates."""
    ...

def millisBetween(date1: Any, date2: Any) -> long:
    """Returns the number of milliseconds between two dates."""
    ...

def daysBetween(date1: Any, date2: Any) -> int:
    """Returns the number of whole days between two dates."""
    ...

def monthsBetween(date1: Any, date2: Any) -> int:
    """Returns the number of whole months between two dates."""
    ...

def yearsBetween(date1: Any, date2: Any) -> int:
    """Returns the number of whole years between two dates."""
    ...

def toMillis(date: Any) -> long:
    """Converts a Date to milliseconds since the Unix epoch."""
    ...

def fromMillis(millis: long) -> Any:
    """Creates a Date from milliseconds since the Unix epoch."""
    ...

def isAfter(date1: Any, date2: Any) -> bool:
    """Returns True if date1 is after date2."""
    ...

def isBefore(date1: Any, date2: Any) -> bool:
    """Returns True if date1 is before date2."""
    ...

def isBetween(targetDate: Any, startDate: Any, endDate: Any) -> bool:
    """Returns True if the target date falls between the start and end dates."""
    ...

def isDaylightTime(date: Any = None) -> bool:
    """Returns True if the given date is in daylight saving time."""
    ...
