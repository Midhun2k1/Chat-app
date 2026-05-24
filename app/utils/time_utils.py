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
        dt = datetime.utcfromtimestamp(val)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
    if isinstance(val, str):
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
