import datetime
import re


def _dt(x):
    if '-' in x:
        return datetime.datetime.strptime(x, '%Y-%m-%d').date()
    return datetime.datetime.strptime(x, '%Y/%m/%d').date()


def _dtt(x):
    from dateutil.parser import parse
    return parse(x)


def rgb_to_hex(rgb_string):
    """Convert RGB color string to hexadecimal"""
    # Handle rgba format by extracting just the RGB values
    if rgb_string.startswith('rgba'):
        # Extract numbers from rgba(r, g, b, a) format
        numbers = re.findall(r'\d+', rgb_string)
        r, g, b = int(numbers[0]), int(numbers[1]), int(numbers[2])
    elif rgb_string.startswith('rgb'):
        # Extract numbers from rgb(r, g, b) format
        numbers = re.findall(r'\d+', rgb_string)
        r, g, b = int(numbers[0]), int(numbers[1]), int(numbers[2])
    else:
        # Color might already be in hex or named format
        return rgb_string

    # Convert to hex
    return f"#{r:02x}{g:02x}{b:02x}"
