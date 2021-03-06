# Point-to-box
> A set of models, tools, and tutorials for the automation of annotating individual objects in images.


This file will become your README and also the index of your documentation.

## Install

`pip install point_to_box`

## How to use

**WORK IN PROGRESS**

The library performs three major functions:

- converting COCO-style object detection images and annotations into point-to-box style images and annotations
- training prompted class-agnostic, single-object localization models
- providing access to models pretrained on COCO data

### Manipulating data

#### Converting data

The `point_to_box.data` module can transform COCO object-detection style images and annotations into point-to-box style images and annotations using a `ConversionDataset`

```python
#hide_output
dataset = data.ConversionDataset(data_path = SRC, anno_fname = ANNOS,
                                 dst_path = DST, img_size = 224, n = 3)
```

A ConversionDataset can turn images with box annotations like this:


![png](docs/images/output_7_0.png)


Into individual images with point-to-box style annotations like this:


![png](docs/images/output_9_0.png)


The ConversionDataset class has a `convert` method to convert individual images one at a time as well as a `convert_all` method to process all (or a percentage) of the images.

```python
#hide_output
# dataset.convert(184791)
dataset.convert_all(cord_format = 'corner_ofst_frac')
```

The `to_json()` method writes the new annotations to file and can split the data into training and validation partitions using the `pct` argument. If no percentage is specified the dataset remains unparitioned and is written to a single directory.

```python
#hide_output
dataset.to_json(pct = 0.15)
```

#### Using data

The `point_to_box.data` module contains a `PTBDataset` class designed in the PyTorch style so it can be used with a PyTorch `DataLoader`.

```python
#hide_output
ptbdata = data.PTBDataset(
    root = DST/'train',
    annos = DST/('train/train_individual_'+ANNOS))

ptbloader = torch.utils.data.DataLoader(dataset = ptbdata, batch_size = 8, shuffle = True)
```

```python
# temp_json = json.load(open(DST/('temp/train/train_individual_'+ANNOS)))
# temp_json
```

Plotting a batch of images from our converted data let's us confirm that the cropping and box coordinate conversion works as we expect it to.


![png](docs/images/output_18_0.png)


```python
batch_boxes
```




    tensor([[0.4053, 0.3105, 0.2121, 0.2171],
            [0.5727, 0.3636, 0.7435, 0.3228],
            [0.0705, 0.3747, 0.1410, 0.7437],
            [0.6778, 0.6000, 0.3280, 0.3393],
            [0.5517, 0.1674, 0.8208, 0.3298],
            [0.4160, 0.5577, 0.4859, 0.7700],
            [0.5455, 0.5545, 0.0424, 0.0477],
            [0.5563, 0.5912, 0.8664, 0.7966]])



### Training models

```python
effloc = model.EfficientLoc(version='efficientnet-b0')
```

    Loaded pretrained weights for efficientnet-b0


```python
# b1 liner 100
# Training complete in 49m 22s
# Best val Loss: 0.0359
# EfficientLoc-b1-coco2017val_40e_imgnetnorm4ch_100L.pth
# effloc.save(DST/'EfficientLoc-b1-coco2017val_40e_imgnetnorm4ch_100L.pth')
```

```python
# b2 liner 100
# Training complete in 51m 0s
# Best val Loss: 0.0357
# EfficientLoc-b2-coco2017val_40e_imgnetnorm4ch_100L.pth
# effloc.save(DST/'EfficientLoc-b2-coco2017val_40e_imgnetnorm4ch_100L.pth')
```

```python
# b3 liner 100
# Training complete in 61m 44s
# Best val Loss: 0.0353

# EfficientLoc-b3-coco2017val_40e_imgnetnorm4ch_100L.pth
# effloc.save(DST/'EfficientLoc-b3-coco2017val_40e_imgnetnorm4ch_100L.pth')
```

```python
# b3 linear out_features 
# Training complete in 61m 47s
# Best val Loss: 0.0347

# EfficientLoc-b3-coco2017val_40e_imgnetnorm4ch_4L.pth
# effloc.save(DST/'EfficientLoc-b3-coco2017val_40e_imgnetnorm4ch_4L.pth')
```

### Export to onnx
