import os
import random
from collections import defaultdict
from typing import Optional, Callable, Tuple, List

import numpy as np
import torch
from loguru import logger
from tqdm import tqdm

from torch.utils.data import Sampler
from xtrainer.dataset import Image
from xtrainer.dataset.base import BaseDataset
from xtrainer.utils.common import get_images
from xtrainer.augment.functional import letterbox


# old
class BalancedBatchSampler(Sampler):
    def __init__(
        self,
        labels: list,
        batch_size: int
    ) -> None:
        super().__init__(None)
        self.labels = labels
        self.batch_size = batch_size
        self.label_to_indices = defaultdict(list)

        '''{
        0:[idx1,idx2,...],
        1:[],
        2:[],
        ...
        }'''

        for idx, label in enumerate(labels):
            self.label_to_indices[label].append(idx)

        self.nc = len(self.label_to_indices)  # nc!= model.classes
        self.image_per_nc = self.batch_size // self.nc  # images per num of classes

        self.batches = self._create_batches()

    def _create_batches(self) -> list:
        # Shuffle the indices within each label
        for label in self.label_to_indices:
            np.random.shuffle(self.label_to_indices[label])

        min_samples = min(len(indices) for indices in self.label_to_indices.values())

        # num_batches=最少数据的类别最小可以分几份
        num_batches = min_samples // self.image_per_nc

        # bss=[bs,bs,bs,...]
        batches = []
        for _ in range(num_batches):
            batch = []
            for label in self.label_to_indices:
                batch.extend(self.label_to_indices[label][:self.image_per_nc])
                self.label_to_indices[label] = self.label_to_indices[label][self.image_per_nc:]
            np.random.shuffle(batch)
            batches.append(batch)

        return batches

    def __iter__(self):
        np.random.shuffle(self.batches)
        for batch in self.batches:
            yield batch

    def __len__(self) -> int:
        return len(self.batches)


class ClassificationDataset(BaseDataset):
    def __init__(
        self,
        root: str,
        wh: Tuple[int, int],
        loader_type: Optional[str] = 'opencv',
        img_type: Optional[str] = 'RGB',
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
        expanding_rate: Optional[int] = 1,
        cache: Optional[bool] = False
    ):
        super(ClassificationDataset, self).__init__(
            root=root,
            wh=wh,
            loader_type=loader_type,
            img_type=img_type,
            transform=transform,
            target_transform=target_transform,
            cache=cache
        )
        self.find_labels()

        # samples=[(Image,1),(Image,0),...]
        self._samples: List[Tuple[Image, int]] = []

        self.load_data()

        if self._use_cache:
            logger.info(f'Preload image data ...')
            self.cache_images_to_memory()

        self.targets = [s[1] for s in self._samples]  # [1,0,1,0,1,...]
        self._samples_map: List[int] = list(range(len(self._samples)))  # [0,1,2,...,n]

        if expanding_rate > 1:
            self.expand_data(expanding_rate)

        if len(self._samples) == 0:
            logger.warning(f"Found 0 files in sub folders of: {self._root}\n")

    def expand_data(self, rate: int) -> None:
        self._samples_map *= rate
        self.targets *= rate

    def find_labels(self) -> None:
        for d in os.scandir(self._root):
            if d.is_dir():
                self._labels.append(d.name)
        self._labels.sort()

    def load_data(self) -> None:
        for idx in tqdm(range(self.num_of_label), desc='Loading data'):
            # xxx/xxx/0
            # xxx/xxx/1
            target_path = os.path.join(self._root, self.idx2label(idx))

            images: List[str] = get_images(target_path, self._SUPPORT_IMG_FORMAT)

            for image in images:
                self._samples.append((Image(path=image), idx))

        random.shuffle(self._samples)

    def cache_images_to_memory(self) -> None:
        image: Image
        for image, idx in tqdm(self._samples, desc='Preload to memory'):
            im = self._load_image(image.path)
            # pre-resize image
            image.data = letterbox(im, self._wh)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, int]:
        sample_idx = self._samples_map[index]

        image: Image
        label: int
        image, label = self._samples[sample_idx]

        im = image.data if self._use_cache else self._load_image(image.path)

        if self._transform is not None:
            im = self._transform(im)

        if self._target_transform is not None:
            label = self._target_transform(label)

        return im, label

    def __len__(self) -> int:
        return len(self._samples_map)


if __name__ == '__main__':
    from xtrainer.core.preprocess import ClsImageT, ClsTargetT
    from torch.utils.data import DataLoader
    from time import time

    wh = (224, 224)
    t1 = time()
    ds = ClassificationDataset(
        root=r'D:\llf\dataset\danyang\training_data\G\classification\nc3\train\2_youwu',
        wh=wh,
        transform=ClsImageT(wh),
        target_transform=ClsTargetT()
    )
    dl = DataLoader(ds, 8)
    for imgs, target in dl:
        print(imgs.shape)
        print(target)

    t2 = time()
    print(t2 - t1)
