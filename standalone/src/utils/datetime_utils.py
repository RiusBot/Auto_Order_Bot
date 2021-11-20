from datetime import datetime


def timestamp_to_local_datetime(ts):
    return datetime.fromtimestamp(ts)


datetime_format = '%m/%d, %H:%M'
