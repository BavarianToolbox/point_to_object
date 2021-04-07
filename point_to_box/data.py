# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_data.ipynb (unless otherwise specified).

__all__ = ['PTBDataset', 'PTBTransform', 'PTBImage', 'ConversionDataset']

# Cell
#export
import point_to_box.utils as utils
import torch
import os
import shutil
import json
import glob
import numpy as np
from tqdm import tqdm
from cv2 import rectangle, circle
from pycocotools.coco import COCO
from torch.utils.data import Dataset
from PIL import Image
import random

from fastcore.dispatch import typedispatch

from fastai.vision.all import Transform, TensorImage
from fastai.vision.data import get_grid
from fastai.torch_core import show_image
import matplotlib.pyplot as plt

# Cell
class PTBDataset(Dataset):
    """Point-to-box dataset class compatible with pytorch dataloaders

    **Params**

    root : Path to data dir

    annos : annotation json file name

    box_format : optional, format for box cord conversion

    tfms : optional, image transforms

    norm_chnls : optional number of img channels to normalize, required if using tfms

    """

    def __init__(self, root, annos, box_format = None, tfms = None, norm_chnls=None, ):
        self.root = root
        self.tfms = tfms
        if tfms:
            assert norm_chnls in [3,4], 'Improper channel stats for normalization'
        self.norm_chnls = norm_chnls
        self.coco = COCO(annos)
        self.ids = list(sorted(self.coco.imgs.keys()))
        if box_format:
            assert box_format in ['cntr_ofst', 'cntr_ofst_frac',
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
            img = self.tfms(torch.as_tensor(
                    img, dtype = torch.float32).permute(2,0,1))
            img = img.permute(1, 2, 0).numpy()

        # new 4-channel array
        img_4ch = np.zeros([imgh, imgw, 4], dtype = np.float32)
        img_4ch[:,:,:3] = img

        # box coords from annotation json
        xmin, ymin, boxw, boxh = coco_annotation[0]['bbox']

        # convert box coords
        if self.box_format:
            target = utils.convert_cords([xmin, ymin, boxw, boxh],
                                         [imgw, imgh], self.box_format)
        # no box cord conversion
        else:
             target = [xmin, ymin, boxw, boxh]

        target = torch.as_tensor(target, dtype = torch.float32)

        # object prompt centers for 4th-channel image mask
        xcntr, ycntr = coco_annotation[0]['prompt']

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

        return img_4ch, target


    def __len__(self):
        return len(self.ids)

# Cell
class PTBTransform(Transform):
    """Point-to-box dataset class compatible with pytorch dataloaders

    **Params**

    root : Path to data dir

    annos : annotation json file name

    box_format : optional, format for box cord conversion

    tfms : optional, image transforms

    norm_chnls : optional number of img channels to normalize, required if using tfms

    """

    def __init__(self, root, annos, box_format = None, tfms = None, norm_chnls=None, ):
        self.root = root
        self.tfms = tfms
        if tfms:
            assert norm_chnls in [3,4], 'Improper channel stats for normalization'
        self.norm_chnls = norm_chnls
        self.coco = COCO(annos)
        self.ids = list(sorted(self.coco.imgs.keys()))
        if box_format:
            assert box_format in ['cntr_ofst', 'cntr_ofst_frac',
                                  'corner_ofst_frac'], 'Improper box format'
        self.box_format = box_format

    def encodes(self, idx):
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
            img = self.tfms(torch.as_tensor(
                    img, dtype = torch.float32).permute(2,0,1))
            img = img.permute(1, 2, 0).numpy()

        # new 4-channel array
        img_4ch = np.zeros([imgh, imgw, 4], dtype = np.float32)
        img_4ch[:,:,:3] = img

        # box coords from annotation json
        xmin, ymin, boxw, boxh = coco_annotation[0]['bbox']

        # convert box coords
        if self.box_format:
            target = utils.convert_cords([xmin, ymin, boxw, boxh],
                                         [imgw, imgh], self.box_format)
        # no box cord conversion
        else:
             target = [xmin, ymin, boxw, boxh]

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

        return PTBImage((img_4ch, target))


    def __len__(self):
        return len(self.ids)

# Cell
class PTBImage(tuple):
    def show(self, ctx=None, **kwargs):
        if len(self) > 1:
            img4ch, box = self
#             print(box)
            box = np.array([box.numpy()])
        else:
            img4ch = self

        img = np.array(img4ch[:3,:,:].permute(1, 2, 0)*255, dtype = np.uint8)
#         img = np.array(img4ch[:3,:,:].permute(1, 2, 0))

#         plt.imshow(img)

#         img = Image.fromarray(img)
#         img = img.copy()
#         img = np.float32(img)
#         plt.imshow(img)
        prompt = np.array(img4ch[-1,:,:])
        y, x = np.where(prompt == prompt.max())

        if len(self) > 1:
            img = utils.draw_rect(img, box, box_format = 'corner_ofst_frac')

#         print(type(img))

        image = circle(img, (x[0],y[0]), radius=2, color=(0, 0, 255), thickness=-1)

        return show_image(img, ctx = ctx)


# Cell
@typedispatch
def show_batch(x:PTBImage, y, samples, ctxs = None, max_n = 6,
               nrows = None, ncols = 2, figsize = None, **kwargs):
    if figsize is None: figsize = (ncols*6, max_n//ncols * 3)
    if ctxs is None:
        ctxs = get_grid(min(x[0].shape[0], max_n),
                        nrows = None, ncols = ncols, figsize = figsize)
        type(x)
        type(x[0])
        for i, ctx in enumerate(ctxs): PTBImage((x[0][i], x[1][i])).show(ctx = ctx)

# Cell
class ConversionDataset():
    """
    Class to convert coco-style datasets and annotations into point-to-box style datasets and annotations

    **Params**

    data_path : path to data directory as Pathlib object

    anno_fname : name of coco-style JSON annotation file

    dst_path : destination path for new dataset and annotation file

    crop_size : size of the square crops taken from the original images

    crop_noise : percentage of possible crop size noise

    resize : bool indicating whether to resize cropped images

    img_size : size of new images is 'resize' is True

    box_noise : percentage of possible box noise

    n : number of samples to create form each object
    """
    def __init__(self, data_path, anno_fname, dst_path,
                 crop_size = 100, crop_noise = 0.1, resize = True,
                 img_size = 512, box_noise = 0.2, n = 1, new_anno_fname = None):
        # inputs for dataset processing
        self.data = data_path
        self.annos = anno_fname
        self.dst = dst_path
        self.coco, self.full_img_ids = self.load_annos()
        self.cats = self.coco.loadCats(self.coco.getCatIds())
        self.crop_size = crop_size
        self.crop_noise = crop_noise
        self.resize = resize
        self.img_size = img_size
        self.box_noise = box_noise
        self.n = n
        if new_anno_fname is None:
            self.new_annos = 'individual_'+ self.annos
        else:
            self.new_annos = new_anno_fname

        # running indicies for new imgs and annos
        self.img_idx = 0
        self.anno_idx = 0

        # info for output annotation json
        self.new_img_names = []
        self.new_img_ids = []
        self.new_box_annos = []
        self.new_areas = []
        self.new_prompts = []
        self.new_anno_ids = []
        self.new_cats = []

    def __len__(self):
        return len(self.full_img_ids)

    def load_annos(self):
        """Load coco-style annotations from file"""
        coco = COCO(self.data/self.annos)
        img_ids = list(sorted(coco.imgs.keys()))
        return coco, img_ids

    def load_img(self, img_id):
        """
        Load image, boxes, box centers, and category ids

        **Params**

        img_id : id of an image in the annotation file

        **Returns**

        img : Pillow image

        bboxs : list of box coordinates [[xmin, ymin, ]]

        cntrs : list of box (object) prompts
        """

        # list of annotation ids
        ann_ids = self.coco.getAnnIds(imgIds = img_id)
        # dict of target annotations
        coco_annos = self.coco.loadAnns(ann_ids)
        coco_annos = [anno for anno in coco_annos if anno['iscrowd'] == 0]
        num_objs = len(coco_annos)
        # path for image
        img_path = self.coco.loadImgs(img_id)[0]['file_name']
        # open image
        img = Image.open(os.path.join(self.data, img_path))
        if img.mode == 'L': img = img.convert('RGB')

        # Bounding box format: [xmin, ymin, width, height]
        bboxs = []
#         cntrs = []
        cats = []
        # TODO:
        # figure out how to transfer license data from original to crop
        # licenses = []
        num_pos = []

        for i in range(num_objs):
            xmin = coco_annos[i]['bbox'][0]
            ymin = coco_annos[i]['bbox'][1]
            xmax = xmin + coco_annos[i]['bbox'][2]
            ymax = ymin + coco_annos[i]['bbox'][3]
            bboxs.append([xmin, ymin, xmax, ymax])

#             if xmin >= 0 and ymin >= 0 and xmax >= 0 and ymax >= 0:
#                 num_pos.append(True)
#             else:
#                 num_pos.append(False)

            if 'center' in coco_annos[i]:
                xcent = coco_annos[i]['center'][0]
                ycent = coco_annos[i]['center'][1]
            else:
                xcent = xmin + (coco_annos[i]['bbox'][2]/2)
                ycent = ymin + (coco_annos[i]['bbox'][3]/2)
#             cntrs.append([xcent, ycent])

            cat = self.coco.loadCats(coco_annos[i]['category_id'])

            cats.append(cat[0]['name'])

        prompts = utils.get_prompt_points(coco_annos, self.n)

        assert len(prompts) == len(bboxs), 'Prompt and box length are not the same'

#         if sum(num_pos) != len(prompts):
#             print(f'Not same length!!: {sum(num_pos)}  !=  {len(prompts)}')

        return img, bboxs, prompts, cats #cntrs,


    def noise(self, val, size, pct = 0.2):
        """
        Add noise to value

        **Params**

        val :  value to add noise to

        size : relative size

        pct :  float, percent for interval clipping

        **Return**

        noisy_val : original value with noise added

        """
        low = -int(size * pct)
        high = int(size * pct)
        noise = np.random.randint(low, high+1)
        noisy_val = val + noise
        return noisy_val


    def crop_objs(self, img, bboxs, prompts, cats, inp_crop_size = 100,
        crop_noise = 0.1, resize = True, img_size = 512, box_noise = 0.05):
        """
        Crop individual square images for each object (box) in img

        **Params**

        img : image to take crops from

        bboxs : box coordinates [[xmin,ymin,xmax,ymax]]

        prompts : box (object) prompt coordinates [[(x,y)]]

        crop_size : square corp size

        crop_noise : percent of noise to add to corp size

        img_size : target size for new images

        box_noise : percent of noise to add to box off set

        **Return**

        imgs_crop : list of cropped np.array images

        boxs_crop : list of cropped bbox corrdinates

        prompts_crop : list of cropped object prompt coordinates

        """
        # pillow coorodinates (x,y):
        #   - start  : upper left corner (0,0)
        #   - finish : bottom right corner (w,h)

        w, h = img.size
        assert (inp_crop_size < w and inp_crop_size < h), \
            'crop size is larger than image'

        imgs_crop, boxs_crop, prompts_crop, cats_crop = [], [], [], []

        num_pos = []
        wrong = 0

        # loop over boxes and prompt sets
        for box, prompt, cat in zip(bboxs, prompts, cats):


            xmin, ymin, xmax, ymax = box
            boxw, boxh = xmax - xmin, ymax - ymin
            box_cntr = (xmin + (boxw/2), ymin + (boxh/2))

            # debug
            if xmin >= 0 and ymin >= 0 and xmax >= 0 and ymax >= 0:
                num_pos.append(True)
            else:
                num_pos.append(False)


            # loop over points in prompt (could be more than one per object)
            for point in prompt:

#                 print(f'Box cords before transform: {xmin} {ymin} {xmax} {ymax}')
#                 print(f'Prompt point: {point}')

#                 if (point[0] > xmax) or (point[0] < xmin):
#                     print(f'X prompt {point[0]} box x bounds: {xmin}, {xmax}')
#                 if (point[1] > ymax) or (point[1] < ymin):
#                     print(f'Y prompt {point[1]} box y bounds: {ymin}, {ymax}')

                # add noise to corp size for each prompt point
                crop_size = self.noise(val = inp_crop_size,
                                       size = inp_crop_size, pct = crop_noise)

                # adjust crop size if necessary
                # crop too small, box taking up more than 90% of crop in either dimension
                too_small = (boxw >= (crop_size * 0.9)) or (boxh >= (crop_size * 0.9))
#                 while too_big is True:
                if too_small:
#                     print(too_small)
#                     print(f'Box w: {boxw}  Box h: {boxh}')
#                     print(f'Original crop size: {crop_size}')
                    crop_size = max(boxw, boxh)*(random.uniform(1.2, 1.4))
#                     print(f'Updated crop size : {crop_size}')
#                     too_big = (boxw > crop_size * 0.9) or (boxh > crop_size * 0.9)
                # clip crop size to shortest img dimension
                if crop_size > min(w, h):
#                     print('Crop too big')
                    crop_size = min(w, h)

                if crop_size < max(boxw, boxh):
                    continue

#                 print(f'Img w: {w}  Img h: {h}')
#                 print(f'Crop size: {crop_size}')
#                 print(f'Box width: {boxw}  Box height: {boxh}')

#                 if (boxw > crop_size * 0.9) or (boxh > crop_size * 0.9):
#                     # make crop-size larger
#                     crop_size = max(boxw, boxh)/(random.uniform(0.4, 0.8))

                orig_size = crop_size
#                 print(crop_size)
                # copy image for crop
                cimg = img.copy()

                # starting corp cords
                left = box_cntr[0] - (crop_size / 2)
                upper = box_cntr[1] - (crop_size / 2)

#                 print(f'Before noise left: {left}  upper: {upper}')


                # max difference the starting crop values (left, upper) can be adjusted before
                # interfering with the object box bounds
                max_wd = (xmin - left) - 1
                max_hd = (ymin - upper) - 1
                old_left = left
                old_upper = upper

                # add noise so box isn't always exactly in the center of crop
                left = self.noise(val = left, size = crop_size, pct = box_noise)
                upper = self.noise(val = upper, size = crop_size, pct = box_noise)

#                 print(f'After noise left: {left}  upper: {upper}')

                # check if noise:
                # - pushed crop bounds into box bounds
#                 if left > xmin: left = xmin - 1
#                 if upper > ymin: upper = ymin - 1
                # - pushed crop bounds too far relative to box bounds
                if abs(left - old_left) > max_wd:
                    if left > old_left:
                        left = old_left + max_wd
                    if left < old_left:
                        left = old_left - max_wd

                if abs(upper - old_upper) > max_hd:
                    if upper > old_upper:
                        upper = old_upper + max_hd
                    if upper < old_upper:
                        upper = old_upper - max_hd



                right, lower = left + crop_size, upper + crop_size

                # check and correct for out of bounds crop
                if left < 0:
                    left = 0
                    right = left + crop_size
                if upper < 0:
                    upper = 0
                    lower = upper + crop_size
                if right > w:
                    right = w
                    left = right - crop_size
                if lower > h:
                    lower = h
                    upper = lower - crop_size

                # compute new box coordinates: [xmin, ymin, xmax, ymax]
                xmin_crop = (xmin - left)
#                 if xmin_crop < 0:
#                     print('-'*10)
#                     print(left)
                ymin_crop = (ymin - upper)
                xmax_crop = (xmax - left)
                ymax_crop = (ymax - upper)
                bbox = [xmin_crop, ymin_crop, xmax_crop, ymax_crop]

                # compute relative prompt cords based on image crop
                x_prompt_rel = point[0] - left
                y_prompt_rel = point[1] - upper


                # debug
#                 print(f'Relative box cords: {xmin_crop} {ymin_crop} {xmax_crop} {ymax_crop}')
#                 print(f'Relative prompt point: {x_prompt_rel}  {y_prompt_rel}')



                # check for out of bounds
                if ((x_prompt_rel > crop_size) or (y_prompt_rel > crop_size)):
                    print('-'*100)
                    print(f'X rel: {x_prompt_rel}  Y rel: {y_prompt_rel}  Crop size: {crop_size}')
                    continue

                # crop expects 4-tupple: (left, upper, right, lower)
                img_crop = img.crop((left, upper, right, lower))

                if resize:
                    img_resz, box_resz = utils.resize(img_size,
                        np.array(img_crop), np.array([bbox]))

                    # reszd box cords
                    xmi_resz, ymi_resz, xma_resz, yma_resz = box_resz[0]
                    # clip box cords to image dims
                    if xmi_resz < 0: xmi_resz = 0
                    if ymi_resz < 0: ymi_resz = 0
                    if xma_resz > img_resz.shape[1]: xma_resz = img_resz.shape[1]
                    if yma_resz > img_resz.shape[0]: yma_resz = img_resz.shape[0]
                    box_resz = [xmi_resz, ymi_resz, xma_resz, yma_resz]

                    # compute resized prompt coordinates based on image resize
                    new_size = img_resz.shape[:2]

                    x_scale = new_size[1] / orig_size
                    y_scale = new_size[0] / orig_size

                    x_prompt_rel_resize = x_prompt_rel * x_scale
                    y_prompt_rel_resize = y_prompt_rel * y_scale


                    # debug
#                     print(f'Resized box cords: {xmi_resz} {ymi_resz} {xma_resz} {yma_resz}')
#                     print(f'Resized prompt point: {x_prompt_rel_resize}  {y_prompt_rel_resize}')


#                     check for out of bounds:
                    if ((x_prompt_rel_resize > img_size) or (y_prompt_rel_resize > img_size)):
                        print(f'X rel resize: {x_prompt_rel_resize}  Y rel resize: {y_prompt_rel_resize}  Img size: {img_size}')
#                         wrong += 1

                    prompt_resz = (x_prompt_rel_resize, y_prompt_rel_resize)

                    imgs_crop.append(img_resz)
                    boxs_crop.append(box_resz)
                    prompts_crop.append(prompt_resz)

                # no resize
                else:
                    imgs_crop.append(np.array(img_crop))
                    boxs_crop.append([bbox])
                    prompts_crop.append((x_prompt_rel, y_prompt_rel))

                cats_crop.append(cat)

#         if sum(num_pos) != (len(prompts_crop)/self.n):
#         print(f'Num wrong: {wrong}')

        return imgs_crop, boxs_crop, prompts_crop, cats_crop



    def convert(self, img_id, cord_format = None):
        """
        Convert a single image in the dataset into multipls
        point-to-box style images

        **Params**

        img_id : id of the image in the coco-style annotation file

        coord_format : optional format for bbox conversion, if None then no conversion is applied

        - cnt_ofst         : [xofst, yofst, w, h]
        - cntr_ofst_frac   : [xofst, yofst, w, h] as fraction of image width/height
        - corner_ofst_frac : [xmin, ymin, w, h] as fraction of image width/height

        """
        # load full img and annos
        img, bboxs, prompts, cats = self.load_img(img_id)

        # crop objs
        crop_imgs, crop_bboxs, crop_prompts, crop_cats = self.crop_objs(
            img = img,
            bboxs = np.array(bboxs),
            prompts = prompts,
            cats = cats,
            inp_crop_size = self.crop_size,
            crop_noise = self.crop_noise,
            box_noise = self.box_noise,
            img_size = self.img_size
        )

#         print(f'Cats: {len(crop_cats)}  Crop prompts: {len(crop_prompts)}')

        # loop over crops and save
        for new_img, box, prompt, cat in zip(crop_imgs, crop_bboxs,
                                           crop_prompts, crop_cats):
            # save img
            new_img_name = f'img_{self.img_idx}_anno_{self.anno_idx}_{cat}_.jpg'
            new_img_pth = self.dst/new_img_name
            img = Image.fromarray(new_img)
            img.save(new_img_pth)

            # construct and append annotation info to lists
#             print(f'npbox: {npbox}')
#             box = npbox[0]
#             print(f'box: {box}')
            w, h = box[2] - box[0], box[3] - box[1]
            area = w * h
            if cord_format:
                coco_box = utils.convert_cords(
                    cords = [box[0], box[1], w, h],
                    img_dims = [new_img.shape[1], new_img.shape[0]],
                    cord_format = cord_format
                )
            else:
                coco_box = [box[0], box[1], w, h]

            self.new_img_names.append(new_img_name)
            self.new_img_ids.append(self.img_idx)
            self.new_box_annos.append(coco_box)
            self.new_areas.append(area)
            self.new_prompts.append(prompt)
            self.new_anno_ids.append(self.anno_idx)
            self.new_cats.append(cat)

            self.img_idx += 1
            self.anno_idx += 1


    def convert_all(self, pct = 1.0, cord_format = None):
        """
        Convert all (or a percentage) of photos and annotations in the dataset

        **Params**

        pct : percent of data to write to train partition
        """
        img_ids = self.full_img_ids
        if pct < 1.0:
            stop = int(len(img_ids)*pct)
            img_ids = img_ids[:stop]

        for img_id in tqdm(img_ids):
            self.convert(img_id, cord_format)


    def to_json(self, pct = 0.0, info = None, licenses = None, categories = None):
        """
        Convert new annotations into coco-style json.

        **Params**

        pct : percent of data to write to valid partition

        info : 'info' section for COCO-style JSON

        licenses : 'licenses' section for COCO-style JSON

        categories : 'categories' section for COCO-style JSON

        """
        if info is None:
            info =  self.coco.dataset['info']

        if licenses is None:
            licenses = self.coco.dataset['licenses']

        if categories is None:
            categories = self.coco.dataset['categories']

        images = []
        annotations = []
        size = self.img_size if self.resize else self.crop_size
        for img_id, img_name, anno_id, box, area, prompt, cat in zip(
            self.new_img_ids, self.new_img_names,
            self.new_anno_ids, self.new_box_annos,
            self.new_areas, self.new_prompts, self.new_cats):

            images.append({
                'license': 0,
                'file_name': img_name,
                'width': size,
                'height': size,
                'id': img_id})

            annotations.append({
                'image_id': img_id,
                'id': anno_id,
                'bbox': box,
                'area': area,
                'prompt': prompt,
                'category_id': self.coco.getCatIds(catNms = cat)[0],
                'iscrowd': 0})


        json_data = {
            'info': info,
            'licenses': licenses,
            'images': images,
            'annotations': annotations,
            'categories': categories}

        if pct > 0.0:
            self.split(json_data, pct)

        else:
            with open(self.dst/self.new_annos, 'w') as json_file:
                json.dump(json_data, json_file)


    def split(self, json_data, pct):
        """Randomly splits and moves data into train/valid partitions

        **Params**

        json_data : coco-style json dict to split into two

        pct : percent of data to assign to valid split
        """

        idxs = [i for i in range(len(json_data['images']))]
        random.shuffle(idxs)
        splt = int(len(idxs)*(1-pct))

        train_json ={
            'info' : json_data['info'],
            'licenses' : json_data['licenses'],
            'categories' : json_data['categories'],
            'images' : list(map(json_data['images'].__getitem__, idxs[:splt])),
            'annotations' : list(map(json_data['annotations'].__getitem__, idxs[:splt])),
        }

        val_json = {
            'info' : json_data['info'],
            'licenses' : json_data['licenses'],
            'categories' : json_data['categories'],
            'images' : list(map(json_data['images'].__getitem__, idxs[splt:])),
            'annotations' : list(map(json_data['annotations'].__getitem__, idxs[splt:])),
        }

        # write json files

        train_dir = self.dst/'train'
        val_dir = self.dst/'val'

        train_dir.mkdir(parents = True, exist_ok = True)
        val_dir.mkdir(parents = True, exist_ok = True)

        train_json_fname = train_dir/('train_'+ self.new_annos)
        val_json_fname = val_dir/('val_'+ self.new_annos)

        for data, fname in zip([train_json, val_json],
                               [train_json_fname, val_json_fname]):

            with open(fname, 'w') as file:
                json.dump(data, file)

        # construct id : fname dict
        _, _, filenames = next(os.walk(self.dst))
        img_idx_list = [int(f.split('_')[1]) for f in filenames if f.endswith('.jpg')]
        idx_name_map = {idx:name for idx,name in zip(img_idx_list, filenames)}

        # move images
        for idx in tqdm(idxs[:splt], desc = 'Moving train images'):
            shutil.move(self.dst/idx_name_map[idx], self.dst/f'train/{idx_name_map[idx]}')

        for idx in tqdm(idxs[splt:], desc = 'Moving val images'):
            shutil.move(self.dst/idx_name_map[idx], self.dst/f'val/{idx_name_map[idx]}')
