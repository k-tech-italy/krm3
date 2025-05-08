import datetime


def _dt(x):
    if '-' in x:
        return datetime.datetime.strptime(x, '%Y-%m-%d').date()
    return datetime.datetime.strptime(x, '%Y/%m/%d').date()


def _dtt(x):
    from dateutil.parser import parse
    return parse(x)
