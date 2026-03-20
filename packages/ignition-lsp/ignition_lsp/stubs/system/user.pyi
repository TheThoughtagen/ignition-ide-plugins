"""Type stubs for system.user — auto-generated from api_db."""

from typing import Any, Callable, Optional

def addCompositeSchedule(name: str, scheduleOne: str, scheduleTwo: str) -> UIResponse:
    """Creates a composite schedule by combining two existing schedules."""
    ...

def addHoliday(holiday: HolidayModel) -> UIResponse:
    """Adds a new holiday to the system."""
    ...

def addRole(userSource: str, role: str) -> UIResponse:
    """Adds a new role to the specified user source."""
    ...

def addSchedule(schedule: AbstractScheduleModel) -> UIResponse:
    """Adds a new schedule to the system."""
    ...

def addUser(userSource: str, user: User) -> UIResponse:
    """Adds a new user to the specified user source."""
    ...

def createScheduleAdjustment(startDate: Any, endDate: Any, isAvailable: bool, note: str) -> ScheduleAdjustment:
    """Creates a schedule adjustment (override) for a specific time period."""
    ...

def editHoliday(holidayName: str, holiday: HolidayModel) -> UIResponse:
    """Edits an existing holiday definition."""
    ...

def editRole(userSource: str, oldName: str, newName: str) -> UIResponse:
    """Renames an existing role in the specified user source."""
    ...

def editSchedule(scheduleName: str, schedule: AbstractScheduleModel) -> UIResponse:
    """Edits an existing schedule definition."""
    ...

def editUser(userSource: str, user: User) -> UIResponse:
    """Saves changes to an existing user in the user source, replacing previous data."""
    ...

def getHoliday(holidayName: str) -> HolidayModel:
    """Returns a specific holiday by name."""
    ...

def getHolidayNames() -> list[str]:
    """Returns a list of all configured holiday names."""
    ...

def getHolidays() -> list[HolidayModel]:
    """Returns all holidays available in the system."""
    ...

def getNewUser(userSource: str, username: str) -> User:
    """Creates a new User object for use with addUser(). Does not persist the user until addUser() is called."""
    ...

def getRoles(userSource: str) -> list[str]:
    """Returns all role names defined in the specified user source."""
    ...

def getSchedule(scheduleName: str) -> AbstractScheduleModel:
    """Returns a specific schedule by name."""
    ...

def getScheduledUsers(userSource: str, date: Any = None) -> list[User]:
    """Returns a list of users that are scheduled at the current or specified date/time."""
    ...

def getScheduleNames() -> list[str]:
    """Returns a list of all schedule names available in the system."""
    ...

def getSchedules() -> list[AbstractScheduleModel]:
    """Returns all available schedule models with full configuration information."""
    ...

def getUser(userSource: str, username: str) -> User:
    """Looks up a specific user by username in the given user source."""
    ...

def getUsers(userSource: str) -> list[User]:
    """Returns all users in the specified user source."""
    ...

def getUserSources() -> list[UserSourceMeta]:
    """Returns all user source profiles configured on the Gateway."""
    ...

def isUserScheduled(user: User, date: Any | int = None) -> bool:
    """Checks if a user is currently scheduled or scheduled at a specific date/time."""
    ...

def removeHoliday(holidayName: str) -> UIResponse:
    """Removes a holiday from the system."""
    ...

def removeRole(userSource: str, role: str) -> UIResponse:
    """Removes a role from the specified user source."""
    ...

def removeSchedule(scheduleName: str) -> UIResponse:
    """Removes a schedule from the system."""
    ...

def removeUser(userSource: str, username: str) -> UIResponse:
    """Removes a user from the specified user source."""
    ...
