# https://learnopencv.com/automatic-document-scanner-using-opencv/

# import the necessary packages
import cv2
import numpy as np
from django.conf import settings


def order_points(pts: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Rearrange coordinates.

    to order: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype='float32')
    pts = np.array(pts)
    s = pts.sum(axis=1)
    # Top-left point will have the smallest sum.
    rect[0] = pts[np.argmin(s)]
    # Bottom-right point will have the largest sum.
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    # Top-right point will have the smallest difference.
    rect[1] = pts[np.argmin(diff)]
    # Bottom-left will have the largest difference.
    rect[3] = pts[np.argmax(diff)]
    # return the ordered coordinates
    return rect.astype('int').tolist()


def find_dest(pts: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    (tl, tr, br, bl) = pts
    # Finding the maximum width.
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    # Finding the maximum height.
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))
    # Final destination co-ordinates.
    destination_corners = [[0, 0], [max_width, 0], [max_width, max_height], [0, max_height]]

    return order_points(destination_corners)


def troubleshooting(message: str, img: 'cv2.typing.MatLike') -> None:
    if settings.CV2_SHOW_IMAGES:
        cv2.imshow(message, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def rotate_90(filepath: str, direction: str) -> bool:
    """Turn image by 90 degrees.

    direction must be one of 'left', 'right'
    """
    direction = cv2.ROTATE_90_CLOCKWISE if direction == 'right' else cv2.ROTATE_90_COUNTERCLOCKWISE
    img = cv2.imread(filepath)

    rotated_image = cv2.rotate(img, direction)
    return cv2.imwrite(filepath, rotated_image)


def clean_image(filepath: str) -> 'cv2.typing.MatLike':
    img = cv2.imread(filepath)

    # Resize image to workable size
    dim_limit = 1024
    max_dim = max(img.shape)
    if max_dim > dim_limit:
        resize_scale = dim_limit / max_dim
        img = cv2.resize(img, None, fx=resize_scale, fy=resize_scale)
    # Create a copy of resized original image for later use
    orig_img = img.copy()

    troubleshooting('resized', orig_img)

    # Repeated Closing operation to remove text from the document.
    kernel = np.ones((5, 5), np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel, iterations=3)

    troubleshooting('morpho', img)

    # GrabCut
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    rect = (20, 20, img.shape[1] - 20, img.shape[0] - 20)
    cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
    img = img * mask2[:, :, np.newaxis]

    troubleshooting('grabcut', img)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (11, 11), 0)
    # Edge Detection.
    canny = cv2.Canny(gray, 0, 200)
    canny = cv2.dilate(canny, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

    # Finding contours for the detected edges.
    contours, hierarchy = cv2.findContours(canny, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    # Keeping only the largest detected contour.
    page = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    # Detecting Edges through Contour approximation.
    # Loop over the contours.
    if len(page) == 0:
        troubleshooting('returning', orig_img)
        return orig_img
    for c in page:
        # Approximate the contour.
        epsilon = 0.02 * cv2.arcLength(c, True)
        corners = cv2.approxPolyDP(c, epsilon, True)
        # If our approximated contour has four points.
        if len(corners) == 4:
            break
    # Sorting the corners and converting them to desired shape.
    corners = sorted(np.concatenate(corners).tolist())
    # For 4 corner points being detected.
    corners = order_points(corners)

    destination_corners = find_dest(corners)

    h, w = orig_img.shape[:2]
    # Getting the homography.
    math_like = cv2.getPerspectiveTransform(np.float32(corners), np.float32(destination_corners))
    # Perspective transform using homography.
    final = cv2.warpPerspective(
        orig_img, math_like, (destination_corners[2][0], destination_corners[2][1]), flags=cv2.INTER_LINEAR
    )
    troubleshooting('final', final)

    return final
