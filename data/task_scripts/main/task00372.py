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

import numpy as np
import math
import phyre.creator as creator_lib


def sin(x):
    return math.sin(math.radians(x))


def cos(x):
    return math.cos(math.radians(x))


@creator_lib.define_task_template(
    h1=np.linspace(0.2, 0.8, 5),
    h2=np.linspace(0.1, 0.6, 5),
    w1=np.linspace(0.3, 0.5, 3),
    w2=np.linspace(0.15, 0.3, 3),
    angle=np.linspace(10, 15, 3),
    orientation=['L', 'R'],
    version='1',
)
def build_task(C, h1, h2, w1, w2, angle, orientation):
    scene_width = C.scene.width
    scene_height = C.scene.height

    bar_thickness = 0.02
    # h1 = 0.6
    # h2 = 0.3
    # orientation = 'R'

    # w1 = 0.4
    # w2 = 0.15
    # angle = 5

    ramp_scale = (w1 - bar_thickness * sin(angle)) / cos(angle)
    if orientation == 'L':
        ramp = C.add('static bar', scale=ramp_scale, angle=360 - angle,
                    top=h1 * scene_height,
                    left=0)
        target = C.add('static bar', scale=w2, top=h2 * scene_height,
                       left=ramp.right)

    elif orientation == 'R':
        ramp = C.add('static bar', scale=ramp_scale, angle=angle,
                    top=h1 * scene_height,
                    right=scene_width)
        target = C.add('static bar', scale=w2, top=h2 * scene_height,
                       right=ramp.left)

    gap = (ramp.bottom - target.top) / scene_height
    if gap < 0.1 or gap > 0.3:
        raise creator_lib.SkipTemplateParams

    ball = C.add('dynamic ball', scale=0.1, center_x=ramp.center_x,
                 bottom=ramp.top)

    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING],
    )
    C.set_meta(C.SolutionTier.PRE_BALL)