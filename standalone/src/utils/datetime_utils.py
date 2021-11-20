from datetime import datetime, timezone


def timestamp_to_local_datetime(ts):
    utc_dt = datetime.fromtimestamp(ts)
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
