import re

from datetime import datetime, timedelta

from zoneinfo import ZoneInfo


def get_status_code(error: Exception) -> int | None:

    for attribute in ("status_code","code","status"):

        value = getattr(error,attribute,None)

        if isinstance(value,int):
            return value

        enum_value = getattr(value,"value",None)

        if isinstance(enum_value,int):
            return enum_value
        

    response = getattr(error,"response",None)

    if response is not None:

        status_code = getattr(response,"status_code",None)
        if isinstance(status_code,int):
            return status_code

    return None


def get_error_message(error: Exception) -> str:

    return str(error).lower()

def is_daily_quota_error(error: Exception) -> bool:

    message = get_error_message(error)

    markers = (
        "requestsperday",
        "requests_per_day",
        "generaterequestsperday",
        "daily quota",
        "daily limit",
        "requests per day",
        "quota per day"
    )

    return any(marker in message for marker in markers)


def is_rate_limit_error(error: Exception) -> bool:

    status_code = get_status_code(error)

    if status_code == 429:
        return True

    message = get_error_message(error)
    

    markers = (
        "rate limit",
        "rate_limit",
        "too many requests",
        "resource_exhausted",
        "retry after",
        "retry in"
    )

    return any(marker in message for marker in markers)


def is_transient_server_error(error: Exception) -> bool:

    status_code = (get_status_code(error))

    return status_code is not None and 500 <= status_code <= 599
    


def is_transient_network_error(error: Exception) -> bool:

    if isinstance(
        error,
        (
            TimeoutError,
            ConnectionError,
            ConnectionAbortedError,
            ConnectionResetError,
            OSError
        )
    ):
        return True

    message = get_error_message(error)
    

    markers = (
        "connection reset",
        "connection refused",
        "connection aborted",
        "server disconnected",
        "network error",
        "timeout",
        "timed out",
        "winerror 10053",
        "winerror 10054"
    )

    return any(marker in message for marker in markers)


def extract_retry_after(error: Exception,default: float = 60.0) -> float:

    retry_after = getattr(error,"retry_after",None)

    if isinstance(retry_after,(int,float)):
        return max(float(retry_after),1.0)

    response = getattr(error,"response",None)

    if response is not None:

        headers = getattr(response,"headers",None)

        if headers:

            header_value = headers.get("retry-after")
            
            if header_value:

                try:
                    return max(float(header_value),1.0)

                except ValueError:
                    pass

    message = str(error)

    patterns = (
        r"retry\s+in\s+([\d.]+)\s*s",
        r"retry\s+after\s+([\d.]+)",
        r"retryDelay['\"]?\s*[:=]\s*['\"]?([\d.]+)s",
    )

    for pattern in patterns:

        match = re.search(pattern,message,flags=re.IGNORECASE)

        if match:

            try:

                return max(float(match.group(1)),1.0)


            except ValueError:
                continue

    return default


def seconds_until_gemini_quota_reset() -> float:

    try:

        timezone = ZoneInfo("America/Los_Angeles")

        now = datetime.now(timezone)

        tomorrow = now.date() + timedelta(days=1)

        reset = datetime(
            year=tomorrow.year,
            month=tomorrow.month,
            day=tomorrow.day,
            hour=0,
            minute=0,
            second=5,
            tzinfo=timezone
        )

        seconds = (reset - now).total_seconds()

        return max(seconds,60.0)

    except Exception:

        return 3600.0