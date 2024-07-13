import os
import math
import time
import json
import yaml
import shutil
from typing import Optional, List, Tuple, Union
import numpy as np
from PIL import Image


def round4(data: float) -> float:
    assert isinstance(data, float)
    return round(float(data), 4)


def round8(data: float) -> float:
    assert isinstance(data, float)
    return round(float(data), 8)


def load_json(path: str):
    with open(path, 'r') as config_file:
        data = json.load(config_file)
    return data


def load_yaml(path: str):
    with open(path, encoding='utf-8') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data


def save_json(data, save: str) -> None:
    with open(save, 'w') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))


def save_yaml(data, save: str) -> None:
    with open(save, 'w', encoding='utf-8') as f:
        yaml.dump(data=data, stream=f, allow_unicode=True)


def get_images(path: str, ext: Optional[List[str]] = None) -> List[str]:
    ext = ['.png', '.jpg'] if ext is None else ext
    data = []

    for root, dirs, files in os.walk(path):
        for file in files:
            file_name, file_ext = os.path.splitext(file)
            if file_ext in ext:
                image = os.path.join(root, file)
                data.append(image)
    return data


def get_json_file(path: str) -> List[str]:
    data = []
    for root, dirs, files in os.walk(path):
        for file in files:
            name, suffix = os.path.splitext(file)
            if suffix.lower() == '.json':
                image = os.path.join(root, file)
                data.append(image)
    return data


def timer(func):
    def func_wrapper(*args, **kwargs):
        from time import time
        time_start = time()
        result = func(*args, **kwargs)
        time_end = time()
        time_spend = time_end - time_start
        print(f'🕐 {func.__name__} Spend Time: {format(time_spend, ".3f")}s')
        return result

    return func_wrapper


def get_time(fmt: str = '%Y%m%d_%H%M%S') -> str:
    time_str = time.strftime(fmt, time.localtime())
    return str(time_str)


def error_exit() -> None:
    exit(1)


def check_dir(path: str, clean: bool = False) -> None:
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        if clean:
            shutil.rmtree(path)
            os.makedirs(path)


def get_image_shape(image: Union[np.ndarray, Image.Image]) -> Tuple[int, int]:
    img_w, img_h = -1, -1
    if isinstance(image, Image.Image):
        img_w, img_h = image.size
    elif isinstance(image, np.ndarray):
        img_h, img_w = image.shape
    return img_w, img_h


def check_size(image: np.ndarray, wh: Tuple[int, int]) -> bool:
    img_w, img_h = get_image_shape(image)
    if img_w != wh[0] or img_h != wh[1]:
        return False
    else:
        return True


# if input=wh then output=hw
# if input=hw then output=wh
def exchange_wh(ab: Tuple[int, int]) -> Tuple[int, int]:
    return ab[1], ab[0]


def pil_to_np(img: Image.Image) -> np.ndarray:
    return np.asarray(img) if isinstance(img, Image.Image) else img


def pil_to_pil(img: np.ndarray) -> Image.Image:
    return Image.fromarray(img) if isinstance(img, np.ndarray) else img
def align_data_size(data1: int, data2: int) -> Tuple[int, int]:
    assert data1 != 0
    assert data2 != 0

    expanding_rate1 = 1
    expanding_rate2 = 1

    if data1 > data2:
        difference = data1 - data2
        expanding_rate1 = 0
    else:
        difference = data2 - data1
        expanding_rate2 = 0

    expanding_rate1 *= math.ceil(difference / data1)
    expanding_rate2 *= math.ceil(difference / data2)

    return expanding_rate1, expanding_rate2
