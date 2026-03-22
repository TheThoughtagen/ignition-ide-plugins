"""Type stubs for system.net — auto-generated from api_db."""

from typing import Any, Callable, Optional

def httpGet(url: str, connectTimeout: int = 10000, readTimeout: int = 60000, username: str = None, password: str = None, headerValues: dict[str, Any] = None, bypassCertValidation: bool = False, useCaches: bool = True, throwOnError: bool = True) -> str:
    """Retrieves the document at the given URL using HTTP GET and returns it as a string."""
    ...

def httpPost(url: str, postData: str | dict[str, Any], contentType: str = "application/x-www-form-urlencoded", connectTimeout: int = 10000, readTimeout: int = 60000, username: str = None, password: str = None, headerValues: dict[str, Any] = None, bypassCertValidation: bool = False) -> str:
    """Sends an HTTP POST request to the given URL and returns the response as a string."""
    ...

def httpPut(url: str, putData: str, contentType: str = "text/plain", connectTimeout: int = 10000, readTimeout: int = 60000, username: str = None, password: str = None, headerValues: dict[str, Any] = None, bypassCertValidation: bool = False) -> str:
    """Sends an HTTP PUT request to the given URL and returns the response as a string."""
    ...

def httpDelete(url: str, contentType: str = "text/plain", connectTimeout: int = 10000, readTimeout: int = 60000, username: str = None, password: str = None, headerValues: dict[str, Any] = None, bypassCertValidation: bool = False) -> str:
    """Sends an HTTP DELETE request to the given URL and returns the response as a string."""
    ...

def httpClient(timeout: int = 60000, bypass_cert_validation: bool = True, username: str = None, password: str = None, proxy: str = None, cookie_policy: str = None, redirect_policy: str = None, version: str = None) -> JythonHttpClient:
    """Creates a reusable HTTP client for sending and receiving HTTP requests. Wraps Java's HttpClient."""
    ...

def openURL(url: str) -> None:
    """Opens the given URL or URI scheme in the host OS default application."""
    ...

def sendEmail(smtp: str = None, fromAddr: str, subject: str = None, body: str = None, html: bool = False, to: list[str], attachmentNames: list[str] = None, attachmentData: list[bytes] = None, timeout: int = 300000, username: str = None, password: str = None, priority: str = 3, smtpProfile: str = None, cc: list[str] = None, bcc: list[str] = None, retries: int = 0, replyTo: str = None) -> None:
    """Sends an email through the given SMTP server or SMTP profile."""
    ...

def getHostName() -> str:
    """Returns the hostname of the computer that the script is running on."""
    ...

def getIpAddress() -> str:
    """Returns the IP address of the computer that the script is running on."""
    ...

def getRemoteServers(runningOnly: bool = True) -> list[str]:
    """Returns a list of Gateway Network servers visible from the local Gateway."""
    ...
