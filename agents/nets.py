# Copyright (c) Facebook, Inc. and its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
import torch.nn as nn
import torchvision

import phyre

USE_CUDA = torch.cuda.is_available()
DEVICE = torch.device('cuda:0' if USE_CUDA else 'cpu')


class ActionNetwork(nn.Module):

    def __init__(self, action_size, output_size, hidden_size=256, num_layers=1):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(action_size, hidden_size)])
        for _ in range(1, num_layers):
            self.layers.append(nn.Linear(hidden_size, hidden_size))
        self.output = nn.Linear(hidden_size, output_size)

    def forward(self, tensor):
        for layer in self.layers:
            tensor = nn.functional.relu(layer(tensor), inplace=True)
        return self.output(tensor)


class FilmActionNetwork(nn.Module):

    def __init__(self, action_size, output_size, **kwargs):
        super().__init__()
        self.net = ActionNetwork(action_size, output_size * 2, **kwargs)

    def forward(self, actions, image):
        beta, gamma = torch.chunk(self.net(actions).unsqueeze(-1).unsqueeze(-1),
                                  chunks=2,
                                  dim=1)
        return image * beta + gamma


class SimpleNetWithAction(nn.Module):

    def __init__(self, action_size, action_network_kwargs=None):
        super().__init__()
        action_network_kwargs = action_network_kwargs or {}
        self.stem = nn.Sequential(
            nn.Conv2d(phyre.NUM_COLORS, 3, kernel_size=1, bias=False),
            nn.BatchNorm2d(3),
            nn.ReLU(inplace=True),
            nn.Conv2d(3, 64, kernel_size=7, stride=4, padding=3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=5, stride=2, padding=2, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=5, stride=2, padding=2, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=5, stride=2, padding=2, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, kernel_size=5, stride=2, padding=2, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=5, stride=2, padding=2, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=5, stride=2, padding=2, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )
        self.action_net = ActionNetwork(action_size, 128,
                                        **action_network_kwargs)

    @property
    def device(self):
        if hasattr(self, 'parameters') and next(self.parameters()).is_cuda:
            return 'cuda'
        else:
            return 'cpu'

    def preprocess(self, observations):
        device = self.device
        image = _image_colors_to_onehot(
            observations.to(dtype=torch.long, device=device))
        return dict(features=self.stem(image).squeeze(-1).squeeze(-1))

    def forward(self, observations, actions, preprocessed=None):
        if preprocessed is None:
            preprocessed = self.preprocess(observations)
        return self._forward(actions, **preprocessed)

    def _forward(self, actions, features):
        actions = self.action_net(actions.to(features.device))
        return (actions * features).sum(-1) / (actions.shape[-1]**0.5)

    def ce_loss(self, decisions, targets):
        targets = torch.ByteTensor(targets).float().to(decisions.device)
        return nn.functional.binary_cross_entropy_with_logits(
            decisions, targets)


def _get_fusution_points(fusion_place_spec, max_points):
    if fusion_place_spec == 'all':
        return tuple(range(max_points))
    elif fusion_place_spec == 'none':
        return tuple()
    else:
        return tuple(int(fusion_place_spec),)


class ResNet18FilmAction(nn.Module):

    def __init__(self,
                 action_size,
                 action_layers=1,
                 action_hidden_size=256,
                 fusion_place='last'):
        super().__init__()
        net = torchvision.models.resnet18(pretrained=False)
        conv1 = nn.Conv2d(phyre.NUM_COLORS,
                          64,
                          kernel_size=7,
                          stride=2,
                          padding=3,
                          bias=False)
        self.register_buffer('embed_weights', torch.eye(phyre.NUM_COLORS))
        self.stem = nn.Sequential(conv1, net.bn1, net.relu, net.maxpool)
        self.stages = nn.ModuleList(
            [net.layer1, net.layer2, net.layer3, net.layer4])

        def build_film(output_size):
            return FilmActionNetwork(action_size,
                                     output_size,
                                     hidden_size=action_hidden_size,
                                     num_layers=action_layers)

        assert fusion_place in ('first', 'last', 'all', 'none', 'last_single')

        self.last_network = None
        if fusion_place == 'all':
            self.action_networks = nn.ModuleList(
                [build_film(size) for size in (64, 64, 128, 256)])
        elif fusion_place == 'last':
            # Save module as attribute.
            self._action_network = build_film(256)
            self.action_networks = [None, None, None, self._action_network]
        elif fusion_place == 'first':
            # Save module as attribute.
            self._action_network = build_film(64)
            self.action_networks = [self._action_network, None, None, None]
        elif fusion_place == 'last_single':
            # Save module as attribute.
            self.last_network = build_film(512)
            self.action_networks = [None, None, None, None]
        elif fusion_place == 'none':
            self.action_networks = [None, None, None, None]
        else:
            raise Exception('Unknown fusion place: %s' % fusion_place)
        self.reason = nn.Linear(512, 1)

    @property
    def device(self):
        if hasattr(self, 'parameters') and next(self.parameters()).is_cuda:
            return 'cuda'
        else:
            return 'cpu'

    def preprocess(self, observations):
        image = self._image_colors_to_onehot(observations)
        features = self.stem(image)
        for stage, act_layer in zip(self.stages, self.action_networks):
            if act_layer is not None:
                break
            features = stage(features)
        else:
            features = nn.functional.adaptive_max_pool2d(features, 1)
        return dict(features=features)

    def forward(self, observations, actions, preprocessed=None):
        if preprocessed is None:
            preprocessed = self.preprocess(observations)
        return self._forward(actions, **preprocessed)

    def _forward(self, actions, features):
        actions = actions.to(features.device)
        skip_compute = True
        for stage, film_layer in zip(self.stages, self.action_networks):
            if film_layer is not None:
                skip_compute = False
                features = film_layer(actions, features)
            if skip_compute:
                continue
            features = stage(features)
        if not skip_compute:
            features = nn.functional.adaptive_max_pool2d(features, 1)
        if self.last_network is not None:
            features = self.last_network(actions, features)
        features = features.flatten(1)
        if features.shape[0] == 1 and actions.shape[0] != 1:
            # Haven't had a chance to use actions. So will match batch size as
            # in actions manually.
            features = features.expand(actions.shape[0], -1)
        return self.reason(features).squeeze(-1)

    def ce_loss(self, decisions, targets):
        targets = targets.to(dtype=torch.float, device=decisions.device)
        return nn.functional.binary_cross_entropy_with_logits(
            decisions, targets)

    def _image_colors_to_onehot(self, indices):
        onehot = torch.nn.functional.embedding(
            indices.to(dtype=torch.long, device=self.embed_weights.device),
            self.embed_weights)
        onehot = onehot.permute(0, 3, 1, 2).contiguous()
        return onehot


def _image_colors_to_onehot(indices):
    onehot = torch.nn.functional.embedding(
        indices, torch.eye(phyre.NUM_COLORS, device=indices.device))
    onehot = onehot.pertmute(0, 3, 1, 2).contiguous()
    return onehot
