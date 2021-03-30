# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_data.ipynb (unless otherwise specified).

__all__ = ['PTBDataset', 'ConversionDataset']

# Cell
#export
import point_to_box.utils as utils
import torch
import os
import numpy as np
from cv2 import rectangle
from pycocotools.coco import COCO
from torch.utils.data import Dataset
from PIL import Image
import random
# import matplotlib.pyplot as plt

# Cell
class PTBDataset(Dataset):
    """Point-to-box dataset class compatible with pytorch dataloaders"""

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
class ConversionDataset():
    """Class to convert coco-style datasets and annotations into point-to-box style datasets and annotations"""
    def __init__(self, data_path, anno_fname, dst_path,
                 crop_size = 100, crop_noise = 0.1,
                 resize = True, img_size = 512, box_noise = 0.2):
        """

        **Params**

        data_path : path to data directory as Pathlib object

        anno_fname : name of coco-style JSON annotation file

        dst_path : destination path for new dataset and annotation file

        crop_size : size of the square crops taken from the original images

        crop_noise : percentage of possible crop size noise

        resize : bool indicating whether to resize cropped images

        img_size : size of new images is 'resize' is True

        box_noise : percentage of possible box noise

        """
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

        # running indicies for new imgs and annos
        self.img_idx = 0
        self.anno_idx = 0

        # info for output annotation json
        self.new_img_names = []
        self.new_img_ids = []
        self.new_box_annos = []
        self.new_areas = []
        self.new_cntrs = []
        self.new_anno_ids = []
        self.new_cats = []

#     def __getitem__():

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

        cntrs : list of box (object) centers
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

        # Bounding boxes
        # Coco format: [xmin, ymin, width, height]
        bboxs = []
        cntrs = []
        cats = []
        for i in range(num_objs):
            xmin = coco_annos[i]['bbox'][0]
            ymin = coco_annos[i]['bbox'][1]
            xmax = xmin + coco_annos[i]['bbox'][2]
            ymax = ymin + coco_annos[i]['bbox'][3]
            bboxs.append([xmin, ymin, xmax, ymax])

            if 'center' in coco_annos[i]:
                xcent = coco_annos[i]['center'][0]
                ycent = coco_annos[i]['center'][1]
            else:
                xcent = xmin + (coco_annos[i]['bbox'][2]/2)
                ycent = ymin + (coco_annos[i]['bbox'][3]/2)
            cntrs.append([xcent, ycent])

            cat = self.coco.loadCats(coco_annos[i]['category_id'])

            cats.append(cat[0]['name'])

        return img, bboxs, cntrs, cats


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


    def crop_objs(self,
        img, bboxs, cntrs,
        inp_crop_size = 100,
        crop_noise = 0.1,
        resize = True,
        img_size = 512,
        box_noise = 0.2
        ):
        """
        Crop individual square images for each object (box) in img

        **Params**

        img : image to take crops from

        bboxs : box coordinates [[xmin,ymin,xmax,ymax]]

        cntrr : center box (object) coordinates (x,y)

        crop_size : square corp size

        crop_noise : percent of noise to add to corp size

        img_size : image resz

        box_noise : percent of noise to add to box off set

        **Return**

        imgs_crop :

        boxs_crop :

        centers_crop :

        """
        # pillow coorodinates (x,y):
        #   - start  : upper left corner (0,0)
        #   - finish : bottom right corner (w,h)

        w, h = img.size
        assert (inp_crop_size < w and inp_crop_size < h), \
            'crop size is larger than image'

        # add noise to corp size
        crop_size = self.noise(val = inp_crop_size,
            size = inp_crop_size, pct = inp_crop_size)

        imgs_crop, boxs_crop, centers_crop = [], [], []

        for box, cntr in zip(bboxs, cntrs):

            xmin, ymin, xmax, ymax = box
            crop_size = inp_crop_size

            # adjust crop size based on size of object box
            boxw, boxh = xmax - xmin, ymax - ymin
#             print(f'Box width: {boxw}  Box height: {boxh}')

            # object taking up more than 90% of crop in either dimension
            if ((0.9 * boxw) > crop_size) or ((0.9 * boxh) > crop_size):
                # make crop-size larger
                crop_size = max(boxw, boxh)/(random.uniform(0.4, 0.8))
            # clip to shortest img dimension
            if crop_size > min(w, h): crop_size = min(w, h)

            # copy image for crop
            cimg = img.copy()

            # starting corp cords
            left = cntr[0] - crop_size / 2
            upper = cntr[1] - crop_size / 2

            # add noise so box isn't always
            # exactly in the center of crop
            left = self.noise(val = left,
                size = crop_size,pct = box_noise)

            upper = self.noise(val = upper,
               size = crop_size, pct = box_noise)

            # right = left + crop_size
            right = left + crop_size
            # lower = upper + crop_size
            lower = upper + crop_size

#             print('Crop coords')
#             print(f'Left: {left} Upper: {upper} Right: {right} Lower: {lower}')

            # check and correct for out of bounds crop
            if left < 0:
                left = 0
                right = left + crop_size
            if upper < 0:
                upper = 0
                lower = upper + crop_size
            if right > w:
                right = w
                left = w - crop_size
            if lower > h:
                lower = h
                upper = h - crop_size

            # compute new box coordinates
            # [xmin, ymin, xmax, ymax]
            xmin_crop = (xmin - left) + 1
            ymin_crop = (ymin - upper) + 1
            xmax_crop = (xmax - left) + 1
            ymax_crop = (ymax - upper) + 1

            bbox = [xmin_crop, ymin_crop, xmax_crop, ymax_crop]

#             print('Crop coords after adjustment')
#             print(f'Left: {left} Upper: {upper} Right: {right} Lower: {lower}')

            # crop expects 4-tupple: (left, upper, right, lower)
            img_crop = img.crop((left, upper, right, lower))

            if resize:
                img_resz, box_resz = utils.resize(img_size,
                    np.array(img_crop), np.array([bbox]))

                # reszd box coords
                xmi_resz, ymi_resz, xma_resz, yma_resz = box_resz[0]

                # compute box center
                x_cent_resz = (xmi_resz + (xma_resz - xmi_resz)//2)
                y_cent_resz = (ymi_resz + (yma_resz - ymi_resz)//2)

                # add noise to center point
                x_cent_resz = self.noise(val = x_cent_resz,
                    size = (xma_resz - xmi_resz), pct = 0.1)

                y_cent_resz = self.noise(val = y_cent_resz,
                    size = (yma_resz - ymi_resz), pct = 0.1)

                center_resz = (x_cent_resz, y_cent_resz)

                imgs_crop.append(img_resz)
                boxs_crop.append(box_resz)
                centers_crop.append(center_resz)

            # no resize
            else:
                imgs_crop.append(np.array(img_crop))
                boxs_crop.append(np.array([bbox]))

                # add noise to center point
                x_cent_crop = self.noise(
                    val = (xmax_crop - xmin_crop)//2,
                    size = (xmax_crop - xmin_crop), pct = 0.1)
                y_cent_crop = self.noise(
                    val = (ymax_crop - ymin_crop)//2,
                    size = (ymax_crop - ymin_crop), pct = 0.1)

                centers_crop.append((x_cent_crop,y_cent_crop))

        return imgs_crop, boxs_crop, centers_crop



    def convert(self, img_id):
        """
        Convert a single image in the dataset into multipls
        point-to-box style images

        **Params**

        img_id : id of the image in the coco-style annotation file

        """
        # load full img and annos
        img, bboxs, cntrs, cats = self.load_img(img_id)

        # crop objs
        crop_imgs, crop_bboxs, crop_cntrs = self.crop_objs(
            img = img,
            bboxs = np.array(bboxs),
            centers = cntrs,
            crop_size = self.crop_size,
            crop_noise = self.crop_noise,
            box_noise = self.box_noise,
            img_size = self.img_size
        )

        # loop over crops and save
        for new_img, box, cntr, cat in zip(crop_imgs, crop_bboxs,
                                           crop_cntrs, cats):
            # save img
            new_img_name = f'img_{self.img_idx}_{cat}_{self.anno_idx}.jpg'
            new_img_pth = DST/new_img_name
            img = Image.fromarray(new_img)
            img.save(new_img_pth)
            # construct annotation info

            box = box[0]
            w, h = box[2] - box[0], box[3] - box[1]
            area = w * h
            coco_box = [box[0], box[1], w, h]

            self.new_img_names.append(new_img_name)
            self.new_img_ids.append(self.img_idx)
            self.new_box_annos.append(coco_box)
            self.new_areas.append(area)
            self.new_cntrs.append(cntr)
            self.new_anno_ids.append(self.anno_idx)
            self.new_cats.append(cat)

            self.img_idx += 1
            self.anno_idx += 1


    def to_json(self, info = None, licenses = None, categories = None):
        """
        Convert new annotations into coco-style json
        """
        if info is None:
            info =  self.coco.dataset['info']

        if licenses is None:
            licenses = self.coco.dataset['licenses']

        if categories is None:
            categories = self.coco.dataset['categories']

        images = []
        annotations = []
        size = self.img_size if Resize else self.crop_size
        for img_id, img_name, anno_id, box, area, center, cat in zip(

            self.new_img_ids, self.new_img_names,
            self.new_anno_ids, self.new_box_annos,
            self.new_areas, self.new_cntrs, self.new_cats):

            images.append(
                {
                    'license': license,
                    'file_name': img_name,
                    'width': size,
                    'height': size,
                    'id': img_id
                })

            annotations.append(
                {
                    'image_id': img_id,
                    'id': anno_id,
                    'bbox': box,
                    'area': area,
                    'center': center,
                    'category_id': self.coco.getCatIds(catNms = cat),
                    'iscrowd': 0
                }
            )


    def convert_all(self):
        """
        Loop over all images in priginal dataset and process
        into individual crops of all objects
        """

        for img_id in self.full_img_ids:
            self.convert(img_id)
        # write to json

