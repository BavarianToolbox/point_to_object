# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_data.ipynb (unless otherwise specified).

__all__ = ['PTBDataset', 'foo_bar']

# Cell
#export
from nbdev.showdoc import *
import torch
import os
import numpy as np
from cv2 import rectangle
from pycocotools.coco import COCO
from torch.utils.data import Dataset
from PIL import Image
# import matplotlib.pyplot as plt

# Cell
class PTBDataset(Dataset):
    def __init__(self, root, annos, box_format, tfms = None, norm_chnls=None, ):
        self.root = root
        self.tfms = tfms
        if tfms:
            assert norm_chnls in [3,4], 'Improper channel stats for normalization'
        self.norm_chnls = norm_chnls
        self.coco = COCO(annos)
        self.ids = list(sorted(self.coco.imgs.keys()))
        assert box_format in ['coco', 'cntr_ofst',
                              'cntr_ofst_frac',
                              'corner_ofst_frac'], 'Improper box format'
        self.box_format = box_format

    def __getitem__(self, idx):
        coco = self.coco
        img_id = self.ids[idx]
        ann_ids = coco.getAnnIds(imgIds=img_id)
        coco_annotation = coco.loadAnns(ann_ids)
        path = coco.loadImgs(img_id)[0]['file_name']

        # open input image and convert to np.ndarray
        img = Image.open(os.path.join(self.root, path))
        img = np.array(img, dtype = np.float32) / 255.
        imgh, imgw = img.shape[:2]

        # 3-channel image transforms
        if self.tfms and self.norm_chnls == 3:
            img = self.tfms(
                torch.as_tensor(
                    img, dtype = torch.float32
                ).permute(2,0,1))
            img = img.permute(1, 2, 0).numpy()

        # new 4-channel array
        img_4ch = np.zeros([imgh, imgw, 4], dtype = np.float32)
        img_4ch[:,:,:3] = img

        # box coords form annotation
        xmin, ymin, boxw, boxh = coco_annotation[0]['bbox']

        # Bounding boxes
        if self.box_format == 'coco':
            # Coco format: [xmin, ymin, width, height]
            target = [xmin, ymin, boxw, boxh]
            target = torch.as_tensor(target, dtype = torch.float32)

        else:
            # convert box coords
            target = self.convert_cords(xmin, ymin, boxw,
                                        boxh, imgw, imgh,
                                        self.box_format)
            target = torch.as_tensor(target, dtype = torch.float32)

        # object prompt centers for 4th-channel image mask
        xcntr, ycntr = coco_annotation[0]['center']

        # create center mask and change center value to 1
        # np indexing [row, col] => [cntr_y, cntr_x]
        cntr_mask = np.zeros([int(imgh),int(imgw)], dtype = np.float32)
        cntr_mask[int(ycntr)][int(xcntr)] = 1

        # add mask to img as 4th channel
        img_4ch[:,:,-1] = cntr_mask
        img_4ch = torch.as_tensor(img_4ch, dtype = torch.float32)

        # re-order image sequence
        # from: [w, h, c]
        # to  : [c, w, h]
        img_4ch = img_4ch.permute(2,0,1)

        # 4-channel image transforms
        if self.tfms and self.norm_chnls == 4:
            img_4ch = self.tfms(img_4ch)
#             img = img.permute(1, 2, 0).numpy()

        return img_4ch, target


    def __len__(self):
        return len(self.ids)

# Cell
def foo_bar():
    Print('This is a test function')