from enum import Enum
from typing import List
from .datetime_utils import timestamp_to_local_datetime


class Ohlcv(Enum):
    TIMESTAMP = 0
    OPEN = 1
    HIGH = 2
    LOW = 3
    CLOSE = 4
    AVERAGE = 5


def _get_ohlcv_with_avg(ohlcv: List[List[float]]):
    return list(map(lambda x: x.append(x[0], (x[1] + x[2] + x[3] + x[4]) / 4), ohlcv))


def _find_peak(ohlcv: List[List[float]]):
    peak_idx, peak = len(ohlcv) - 1, ohlcv[-1][Ohlcv.HIGH]
    for idx in range(peak_idx, 0, -1):
        if ohlcv[idx][Ohlcv.HIGH] > peak:
            peak_idx = idx
            peak = ohlcv[idx][Ohlcv.HIGH]
    return peak_idx, ohlcv[peak_idx][Ohlcv.HIGH]


def _find_valley_from_peak(ohlcv: List[List[float]]):
    valley_idx, avg = len(ohlcv) - 1, ohlcv[-1][Ohlcv.AVERAGE]
    for idx in range(valley_idx, 1, -1):
        if ohlcv[idx - 1][Ohlcv.AVERAGE] < avg:
            valley_idx = idx - 1
            avg = ohlcv[idx - 1][Ohlcv.AVERAGE]
        else:
            break
    return valley_idx, ohlcv[valley_idx][Ohlcv.LOW]


def get_fibonacci(ohlcv, fibonacci):
    new_ohlcv = _get_ohlcv_with_avg(ohlcv)
    peak_idx, peak = _find_peak(new_ohlcv)
    valley_idx, valley = _find_valley_from_peak(new_ohlcv[:peak_idx])
    price = valley + (peak - valley) * fibonacci
    start_time = timestamp_to_local_datetime(ohlcv[valley_idx][Ohlcv.TIMESTAMP])
    end_time = timestamp_to_local_datetime(ohlcv[peak_idx][Ohlcv.TIMESTAMP])
    info = f"""
        Fibonacci period: {start_time} -> {end_time}
        Fibonacci range: {round(valley, 4)} -> {round(peak, 4)}
        Fibonacci: {round(fibonacci, 4)}
        Fibonacci price: {round(price * fibonacci, 4)}
        """
    return price, info
