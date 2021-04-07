# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/02_model.ipynb (unless otherwise specified).

__all__ = ['EfficientLoc', 'CIoU']

# Cell
#export

from efficientnet_pytorch import EfficientNet

import copy
import time
import math

import torch
import torch.optim as opt
from torch.utils.data import DataLoader
from torchvision import transforms

# Cell
class EfficientLoc():

    def __init__(self, version = 'efficientnet-b0', in_channels = 4, out_features = 4, export = False):
        """
        EfficientLoc model class for loading, training, and exporting models
        """

        self.version = version


#         self.inter_channels = versoin_dict([version])
        # TODO
        # check version is compliant
        self.in_channels = in_channels
        self.out_features = out_features
        self.export = export
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.data_parallel = False
        self.model = self.get_model(version = self.version,
            in_channels = self.in_channels, out_features  = self.out_features)

    def get_model(self, version, in_channels, out_features):
        """
        Adjusts efficient net model architecture for point-to-box data
        """

        version_chnls = {
            'efficientnet-b0': 1280,
            'efficientnet-b1': 1280,
            'efficientnet-b2': 1408,
            'efficientnet-b3': 1536,
            'efficientnet-b4': 1792
#             'efficientnet-b5': 456
#             'efficientnet-b6': 528
#             'efficientnet-b7': 600
#             'efficientnet-b8': 672
#             'efficientnet-l2': 800

        }

        inter_channel = version_chnls[version]

        model = EfficientNet.from_pretrained(version, include_top = False)

        # adjust in channels in conv stem
        model._change_in_channels(in_channels)

#         if self.export:
        model.set_swish(memory_efficient= (not self.export))

        model = torch.nn.Sequential(
            model,
            torch.nn.Dropout(0.2),
            torch.nn.Flatten(),
            torch.nn.Linear(inter_channel, out_features),
#             torch.nn.Linear(100, out_features),
            torch.nn.Sigmoid()
        )
        for param in model.parameters():
            param.requires_grad = True

        if torch.cuda.device_count() > 1:
            print(f'Using {torch.cuda.device_count()} GPUs')
            model = torch.nn.DataParallel(model)
            self.data_parallel = True


        model.to(self.device)

        return model

    def train(self, dataloaders, criterion, optimizer, num_epochs, ds_sizes, print_every = 100, scheduler=None):
        """
        Training function for model

        **Params**

        loaders : dict of val/train DataLoaders

        criterion : loss function

        optimizer : training optimizer

        num_epochs : number of training epochs

        ds_sizes : dict of number of samples in

        print_every : batch_interval for intermediate loss printing

        scheduler : Optional learning rate scheduler
        """
        train_start = time.time()
        best_model_wts = copy.deepcopy(self.model.state_dict())
        best_loss = 10000000.0

        for epoch in range(num_epochs):

            print(f'Epoch {epoch + 1}/{num_epochs}')
            print('-' * 10)

            # Each epoch has a training and validation phase
            for phase in ['train', 'val']:
                phase_start = time.time()
                if phase == 'train':
                    self.model.train()
                else:
                    self.model.eval()

                inter_loss = 0.
                running_loss = 0.
                batches_past = 0

                # Iterate over data.
                for i, (inputs, labels) in enumerate(dataloaders[phase]):

                    inputs = inputs.to(self.device)
                    labels = labels.to(self.device)

                    # zero the parameter gradients
                    optimizer.zero_grad()

                    # forward, only track history in train phase
                    with torch.set_grad_enabled(phase == 'train'):
                        outputs = self.model(inputs)
                        loss = criterion(outputs, labels)

                        # backward + optimize only if in training phase
                        if phase == 'train':
                            loss.backward()
                            optimizer.step()

                    running_loss += loss.item()
                    inter_loss += loss.item()

                    if (i+1) % print_every == 0:

                        inter_loss = inter_loss / ((i+1-batches_past) * inputs.shape[0])
                        print(f'Intermediate loss: {inter_loss:.6f}')
                        inter_loss = 0.
                        batches_past = i+1

                if phase == 'train' and scheduler is not None:
                    scheduler.step()

                epoch_loss = running_loss / ds_sizes[phase]

                phase_duration = time.time() - phase_start
                phase_duration = f'{(phase_duration // 60):.0f}m {(phase_duration % 60):.0f}s'
                print('-' * 5)
                print(f'{phase} Phase Duration: {phase_duration}  Average Loss: {epoch_loss:.6f} in ')
                print('-' * 5)

                # deep copy the model
                if phase == 'val' and epoch_loss < best_loss:
                    best_loss = epoch_loss
                    best_model_wts = copy.deepcopy(self.model.state_dict())

        time_elapsed = time.time() - train_start
        print(f'Training complete in {(time_elapsed // 60):.0f}m {(time_elapsed % 60):.0f}s')
        print(f'Best val Loss: {best_loss:.4f}')

        # load best model weights
        self.model.load_state_dict(best_model_wts)


    def save(self, dst, info = None):
        """Save model and optimizer state dict

        **Params**

        dst : destination file path including .pth file name

        info : Optional dictionary with model info

        """
        if info:
            torch.save(info, dst)
        else:
            model_dict = self.model.state_dict()
            if self.data_parallel:
                model_dict = self.model.module.state_dict()
            torch.save({
                'base_arch' : self.version,
                'model_state_dict' : model_dict,
            }, dst)

    def load(self, model_state_dict):
        """Load model weights from state-dict"""
        self.model.load_state_dict(model_state_dict)

# Cell
class CIoU(torch.nn.Module):
    """Complete IoU loss class"""

    def __init__(self) -> None:
        super(CIoU, self).__init__()

    def forward(self, input: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        return self.ciou(input, target)
#         return F.l1_loss(input, target, reduction=self.reduction)

    def ciou(self, bboxes1, bboxes2):
        bboxes1 = torch.sigmoid(bboxes1)
        bboxes2 = torch.sigmoid(bboxes2)
        rows = bboxes1.shape[0]
        cols = bboxes2.shape[0]
        cious = torch.zeros((rows, cols))
        if rows * cols == 0:
            return cious
        exchange = False
        if bboxes1.shape[0] > bboxes2.shape[0]:
            bboxes1, bboxes2 = bboxes2, bboxes1
            cious = torch.zeros((cols, rows))
            exchange = True
        w1 = torch.exp(bboxes1[:, 2])
        h1 = torch.exp(bboxes1[:, 3])
        w2 = torch.exp(bboxes2[:, 2])
        h2 = torch.exp(bboxes2[:, 3])
        area1 = w1 * h1
        area2 = w2 * h2
        center_x1 = bboxes1[:, 0]
        center_y1 = bboxes1[:, 1]
        center_x2 = bboxes2[:, 0]
        center_y2 = bboxes2[:, 1]

        inter_l = torch.max(center_x1 - w1 / 2,center_x2 - w2 / 2)
        inter_r = torch.min(center_x1 + w1 / 2,center_x2 + w2 / 2)
        inter_t = torch.max(center_y1 - h1 / 2,center_y2 - h2 / 2)
        inter_b = torch.min(center_y1 + h1 / 2,center_y2 + h2 / 2)
        inter_area = torch.clamp((inter_r - inter_l),min=0) * torch.clamp((inter_b - inter_t),min=0)

        c_l = torch.min(center_x1 - w1 / 2,center_x2 - w2 / 2)
        c_r = torch.max(center_x1 + w1 / 2,center_x2 + w2 / 2)
        c_t = torch.min(center_y1 - h1 / 2,center_y2 - h2 / 2)
        c_b = torch.max(center_y1 + h1 / 2,center_y2 + h2 / 2)

        inter_diag = (center_x2 - center_x1)**2 + (center_y2 - center_y1)**2
        c_diag = torch.clamp((c_r - c_l),min=0)**2 + torch.clamp((c_b - c_t),min=0)**2

        union = area1+area2-inter_area
        u = (inter_diag) / c_diag
        iou = inter_area / union
        v = (4 / (math.pi ** 2)) * torch.pow((torch.atan(w2 / h2) - torch.atan(w1 / h1)), 2)
        with torch.no_grad():
            S = (iou>0.5).float()
            alpha= S*v/(1-iou+v)
        cious = iou - u - alpha * v
        cious = torch.clamp(cious,min=-1.0,max = 1.0)
        if exchange:
            cious = cious.T
        return torch.sum(1-cious)