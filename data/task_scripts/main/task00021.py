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



def cos(x):
    return math.cos(math.radians(x))


@creator_lib.define_task_template(
    h0=np.linspace(0.2, 0.5, 15),
    w1=np.linspace(0.1, 0.2, 3),
    w2=np.linspace(0.15, 0.3, 3),
    angle=np.linspace(10, 20, 3),
    search_params=dict(
        max_search_tasks=300,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
    ),
    version='1'
)
def build_task(C, h0, w1, w2, angle):
    scene_width = C.scene.width
    scene_height = C.scene.height

    # h0 = 0.6
    # w1 = 0.1
    # w2 = 0.15
    # w3 = 0.1
    # w4 = 0.25
    # w5 = 0.1
    # w6 = 0.1
    eps = 0.005 * scene_width
    # angle = 15

    ramp1 = C.add('static bar', angle=360 - angle,
                  scale=w1 / cos(angle),
                  left=0,
                  bottom=h0 * scene_height)
    teeter1 = C.add('dynamic bar', scale=w2,
                    left=ramp1.right + eps,
                    bottom=ramp1.bottom)
    fulcrum1 = C.add('static ball', scale=0.05,
                     center_x=teeter1.center_x,
                     top=teeter1.bottom)
    fulcrum1b = C.add('static ball', scale=0.05,
                      right=teeter1.right,
                      top=teeter1.bottom)
    floor1 = C.add('static bar', scale=w2,
                   left=teeter1.left,
                   top=fulcrum1.bottom)

    ramp2 = C.add('static bar', angle=360-angle,
                  scale=w1 / cos(angle),
                  left=teeter1.right + eps,
                  top=teeter1.top)
    teeter2 = C.add('static jar', scale=w2,
                    left=ramp2.right + eps,
                    top=ramp2.bottom)

    ramp3 = C.add('static bar', angle=360-angle,
                  scale=w1 / cos(angle),
                  left=teeter2.right + eps,
                  top=teeter2.top)
    w6 = 1.0 - w1 - w2 - w1 - w2 - w1 - 5 * eps / scene_width
    if w6 < 0.2:
        raise creator_lib.SkipTemplateParams
    target = C.add('static bar', scale=w6,
                   left=ramp3.right + eps,
                   bottom=ramp3.bottom)

    ball = C.add('dynamic ball', scale=0.05,
                 left=0,
                 bottom=ramp1.top)

    ceil = C.add('static bar', scale=1.0,
                 left=0,
                 top=ball.top + 0.1 * scene_height)

    if ceil.top > scene_height or target.bottom < 0 or teeter2.bottom < 0:
        raise creator_lib.SkipTemplateParams

    C.update_task(
        body1=ball,
        body2=teeter2,
        relationships=[C.SpatialRelationship.TOUCHING],
    )
    C.set_meta(C.SolutionTier.BALL)
