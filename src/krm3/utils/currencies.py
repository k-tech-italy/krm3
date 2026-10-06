import decimal


def rounding(currency, value):  # noqa: ANN001, ANN201
    if not isinstance(value, decimal.Decimal):
        value = decimal.Decimal(value)
    # TODO: fix to use currency for number of decimals
    return value.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
