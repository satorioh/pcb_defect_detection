import os
import time
import cv2
from multiprocessing import Pool, Manager, Lock
from utils import get_file_paths
from functools import partial

template_dir = './dataset/Template-PCB-images'
test_image_dir = './dataset/Defective-PCB-images'

template_data = get_file_paths(template_dir, is_template=True)
test_image_data = get_file_paths(test_image_dir, suffix='.jpg')


def get_match_template(image_path):
    print(f'Processing {image_path}...')
    test_image_gray = cv2.imread(image_path, 0)
    h, w = test_image_gray.shape
    result = []
    for template_path, template_label in template_data:
        template_gray = cv2.imread(template_path, 0)
        t_h, t_w = template_gray.shape
        if h > t_h or w > t_w:
            continue
        match = cv2.matchTemplate(test_image_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
        result.append((template_path, template_label, max_val))
    result.sort(key=lambda x: x[2], reverse=True)
    return result[0]


def get_binary_image(image):
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized_image = cv2.resize(image_gray, (750, 450))
    blur_image = cv2.GaussianBlur(resized_image, (3, 3), 0)
    image_adap_thresh = cv2.adaptiveThreshold(blur_image, 255,
                                              cv2.ADAPTIVE_THRESH_MEAN_C,
                                              cv2.THRESH_BINARY, 15, 5)
    return image_adap_thresh


def get_subtract_image(image_1, image_2):
    sub_img = cv2.subtract(image_1, image_2)
    return cv2.medianBlur(sub_img, 5)


def find_contours(final_img):
    cnts = cv2.findContours(final_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[-2]
    blobs = []
    for cnt in cnts:
        if 0 < cv2.contourArea(cnt) < 300:
            blobs.append(cnt)
    return blobs


def draw_contours(rgb_test_img, contours):
    rgb_test_img_resize = cv2.resize(rgb_test_img, (750, 450))
    draw_img = rgb_test_img_resize.copy()
    return cv2.drawContours(draw_img, contours, -1, (255, 0, 0), 2)


def save_image(image, image_path):
    # img_path: ./dataset/Defective-PCB-images/Missing_hole/Missing_hole_01_left/01_missing_hole_10.jpg
    # save res to ./dist/Defective-PCB-images/Missing_hole/Missing_hole_01_left/01_missing_hole_10.jpg
    print(f'Saving image...')
    save_path = image_path.replace('dataset', 'dist')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    cv2.imwrite(save_path, image)
    print(f'Saved image to {save_path}')


def calc_result(image_label, template_label, return_dict, lock, contours_len):
    with lock:
        return_dict['total'] += 1
        if contours_len == 0:
            return_dict['miss'] += 1
        if image_label == template_label:
            return_dict['correct'] += 1
        else:
            return_dict['error'] += 1
    print(return_dict)


def process(image_data, return_dict, lock):
    test_image_path, test_image_label = image_data
    template_path, template_label, max_val = get_match_template(test_image_path)
    test_image_rgb = cv2.imread(test_image_path)
    template_image_rgb = cv2.imread(template_path)
    test_image_binary = get_binary_image(test_image_rgb)
    template_image_binary = get_binary_image(template_image_rgb)
    subtract_image = get_subtract_image(test_image_binary, template_image_binary)
    contours = find_contours(subtract_image)
    contours_len = len(contours)
    print(f"{contours_len} defects found in {test_image_path}")
    res = draw_contours(test_image_rgb, contours)
    save_image(res, test_image_path)
    calc_result(test_image_label, template_label, return_dict, lock, contours_len)


def main():
    manager = Manager()
    return_dict = manager.dict({
        'total': 0,
        'correct': 0,
        'error': 0,
        'miss': 0
    })
    lock = manager.Lock()
    pool = Pool(os.cpu_count())
    process_with_dict = partial(process, return_dict=return_dict, lock=lock)
    pool.map(process_with_dict, test_image_data)
    pool.close()
    pool.join()
    print(return_dict)  # {'total': 663, 'correct': 663, 'error': 0}


if __name__ == '__main__':
    start_time = time.time()
    main()
    print(f'Elapsed time: {time.time() - start_time:.2f}s')  # Elapsed time: 110.32s
