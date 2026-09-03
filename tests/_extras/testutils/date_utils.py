import datetime

from dateutil.parser import parse


def _dt(x):
    if len(x) == 8:
        return datetime.datetime.strptime(x, '%Y%m%d').date()
    if '-' in x:
        return datetime.datetime.strptime(x, '%Y-%m-%d').date()
    return datetime.datetime.strptime(x, '%Y/%m/%d').date()


def _dtt(x):
    return parse(x)
