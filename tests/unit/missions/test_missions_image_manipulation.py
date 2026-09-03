from pathlib import Path

import cv2
import numpy as np

from krm3.missions.transform import clean_image

EXAMPLES = Path(__file__).parent / 'examples'

# OpenCV SIMD code paths differ across CPUs and builds, shifting a few pixel values by 1-2 units
MAX_PIXEL_DIFFERENCE = 3


def test_image_cleaning(expense):
    expected = cv2.imread(str(EXAMPLES / 'expected.png'))

    obtained = clean_image(str(EXAMPLES / 'original.jpg'))
    # TO write expected: cv2.imwrite(str(EXAMPLES / 'expected.png'), obtained)

    assert obtained.shape == expected.shape
    assert np.abs(obtained.astype(int) - expected.astype(int)).max() <= MAX_PIXEL_DIFFERENCE
