"""
CS 6375 Homework 2 Programming
Implement the create_modules() function in this python script
"""
import os
import math
import torch
import torch.nn as nn
import numpy as np

# the YOLO network class
class YOLO(nn.Module):
    def __init__(self, num_boxes, num_classes):
        super(YOLO, self).__init__()
        self.num_boxes = num_boxes
        self.num_classes = num_classes
        self.image_size = 448
        self.grid_size = 64

        # Register the sequential network as an attribute
        self.network = self.create_modules()
        
        # initialize weights
        for m in self.network.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    # Implement the create_modules function to build the network
    def create_modules(self):
        modules = nn.Sequential()

        # Conv1 + ReLU1 + MaxPool1
        modules.add_module("Conv1", nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1))  # (16, 448, 448)
        modules.add_module("ReLU1", nn.ReLU())
        modules.add_module("MaxPool1", nn.MaxPool2d(kernel_size=2, stride=2))  # (16, 224, 224)

        # Conv2 + ReLU2 + MaxPool2
        modules.add_module("Conv2", nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1))  # (32, 224, 224)
        modules.add_module("ReLU2", nn.ReLU())
        modules.add_module("MaxPool2", nn.MaxPool2d(kernel_size=2, stride=2))  # (32, 112, 112)

        # Conv3 + ReLU3 + MaxPool3
        modules.add_module("Conv3", nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1))  # (64, 112, 112)
        modules.add_module("ReLU3", nn.ReLU())
        modules.add_module("MaxPool3", nn.MaxPool2d(kernel_size=2, stride=2))  # (64, 56, 56)

        # Conv4 + ReLU4 + MaxPool4
        modules.add_module("Conv4", nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1))  # (128, 56, 56)
        modules.add_module("ReLU4", nn.ReLU())
        modules.add_module("MaxPool4", nn.MaxPool2d(kernel_size=2, stride=2))  # (128, 28, 28)

        # Conv5 + ReLU5 + MaxPool5
        modules.add_module("Conv5", nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1))  # (256, 28, 28)
        modules.add_module("ReLU5", nn.ReLU())
        modules.add_module("MaxPool5", nn.MaxPool2d(kernel_size=2, stride=2))  # (256, 14, 14)

        # Conv6 + ReLU6 + MaxPool6
        modules.add_module("Conv6", nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1))  # (512, 14, 14)
        modules.add_module("ReLU6", nn.ReLU())
        modules.add_module("MaxPool6", nn.MaxPool2d(kernel_size=2, stride=2))  # (512, 7, 7)

        # Conv7 + ReLU7
        modules.add_module("Conv7", nn.Conv2d(512, 1024, kernel_size=3, stride=1, padding=1))  # (1024, 7, 7)
        modules.add_module("ReLU7", nn.ReLU())

        # Conv8 + ReLU8
        modules.add_module("Conv8", nn.Conv2d(1024, 1024, kernel_size=3, stride=1, padding=1))  # (1024, 7, 7)
        modules.add_module("ReLU8", nn.ReLU())

        # Conv9 + ReLU9
        modules.add_module("Conv9", nn.Conv2d(1024, 1024, kernel_size=3, stride=1, padding=1))  # (1024, 7, 7)
        modules.add_module("ReLU9", nn.ReLU())

        # Flatten
        modules.add_module("Flatten", nn.Flatten())  # Flatten into a single dimension (1024 * 7 * 7 = 50176)

        # Fully Connected Layer 1
        modules.add_module("FC1", nn.Linear(1024 * 7 * 7, 256))  # Fully connected layer (256 units)
        modules.add_module("ReLU_FC1", nn.ReLU())

        # Fully Connected Layer 2
        modules.add_module("FC2", nn.Linear(256, 256))  # Fully connected layer (256 units)
        modules.add_module("ReLU_FC2", nn.ReLU())

        # Output Layer
        output_size = self.num_boxes * 5 + self.num_classes  # 5B + C
        modules.add_module("Output", nn.Linear(256, output_size * 7 * 7))

        return modules

    # Undo normalization to obtain bounding boxes in the original image space
    def transform_predictions(self, output):
        batch_size = output.shape[0]
        x = torch.linspace(0, 384, steps=7)
        y = torch.linspace(0, 384, steps=7)
        corner_x, corner_y = torch.meshgrid(x, y, indexing='xy')
        corner_x = torch.unsqueeze(corner_x, dim=0)
        corner_y = torch.unsqueeze(corner_y, dim=0)
        corners = torch.cat((corner_x, corner_y), dim=0)
        corners = corners.unsqueeze(0).repeat(batch_size, 1, 1, 1)
        pred_box = output.clone()

        for i in range(self.num_boxes):
            pred_box[:, i*5, :, :] = corners[:, 0, :, :] + output[:, i*5, :, :] * self.grid_size
            pred_box[:, i*5+1, :, :] = corners[:, 1, :, :] + output[:, i*5+1, :, :] * self.grid_size
            pred_box[:, i*5+2, :, :] = output[:, i*5+2, :, :] * self.image_size
            pred_box[:, i*5+3, :, :] = output[:, i*5+3, :, :] * self.image_size

        return pred_box

    # forward pass of the YOLO network
    def forward(self, x):
        output = self.network(x).reshape((-1, self.num_boxes * 5 + self.num_classes, 7, 7))
        pred_box = self.transform_predictions(output)
        return output, pred_box

# run this main function for testing
if __name__ == '__main__':
    network = YOLO(num_boxes=2, num_classes=1)
    print(network)

    image = np.random.uniform(-0.5, 0.5, size=(1, 3, 448, 448)).astype(np.float32)
    image_tensor = torch.from_numpy(image)
    print('Input image:', image_tensor.shape)

    output, pred_box = network(image_tensor)
    print('Network output:', output.shape, pred_box.shape)
