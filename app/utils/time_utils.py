from datetime import datetime, timezone

def format_datetime_to_zulu(val) -> str:
    """
    Standardizes datetime and timestamp serialization to Zulu ISO 8601 string format
    with microsecond precision (e.g. 'YYYY-MM-DDTHH:MM:SS.ffffffZ').
    """
    if val is None:
        return ""
    if isinstance(val, datetime):
        # Convert to UTC if timezone-aware
        if val.tzinfo is not None:
            val = val.astimezone(timezone.utc)
        return val.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
    if isinstance(val, (int, float)):
        # Convert epoch to datetime
        # Check if timestamp is in milliseconds (usually > 1e11)
        if val > 1e11:
            val = val / 1000.0
        dt = datetime.fromtimestamp(val, timezone.utc)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
    if isinstance(val, str):
        # Check if the string represents a numeric timestamp
        try:
            num = float(val)
            if num > 1e11:
                num = num / 1000.0
            dt = datetime.fromtimestamp(num, timezone.utc)
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
        except ValueError:
            pass

        if val.endswith('z'):
            return val[:-1] + 'Z'
        if val.endswith('Z') and 'T' in val:
            return val
        try:
            cleaned = val.replace('Z', '').replace('z', '')
            dt = datetime.fromisoformat(cleaned)
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
        except Exception:
            return val
    return str(val)


def parse_datetime(val) -> datetime:
    """
    Parses a datetime from various formats (datetime object, epoch, string)
    and returns a timezone-aware UTC datetime.
    """
    if val is None or val == "" or val in ("null", "None"):
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, (int, float)):
        # Check if timestamp is in milliseconds (usually > 1e11)
        if val > 1e11:
            val = val / 1000.0
        return datetime.fromtimestamp(val, timezone.utc)
    if isinstance(val, str):
        # Check if the string represents a numeric timestamp
        try:
            num = float(val)
            if num > 1e11:
                num = num / 1000.0
            return datetime.fromtimestamp(num, timezone.utc)
        except ValueError:
            pass

        try:
            cleaned = val.replace('Z', '+00:00').replace('z', '+00:00')
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)
