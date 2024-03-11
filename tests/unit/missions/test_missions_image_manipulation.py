import hashlib
from io import BytesIO
from pathlib import Path

import cv2

from krm3.missions.transform import clean_image


def test_image_cleaning(expense):
    expected = (Path(__file__).parent / 'examples/expected.jpg').read_bytes()
    expected = hashlib.sha256(expected).hexdigest()

    obtained = clean_image(str(Path(__file__).parent / 'examples/original.jpg'))
    is_success, buffer = cv2.imencode('.jpg', obtained)
    io_buf = BytesIO(buffer)
    obtained = hashlib.sha256(io_buf.getbuffer()).hexdigest()

    assert obtained == expected, 'Images should be identical'
