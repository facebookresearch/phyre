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


@creator_lib.define_task_template(
    x=np.linspace(0.2, 0.8, 10),
    y=np.linspace(0.2, 0.5, 10),
    bar_size=np.linspace(0.05, 0.1, 5),
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
        max_search_tasks=500,
    ),
    version='2',
)
def build_task(C, x, y, bar_size):

    scene_width = C.scene.width
    scene_height = C.scene.height

    target = C.add('static bar', scale=1.0, left=0, bottom=0)

    angle = 5
    eps = 0.001
    lbar = C.add('static bar', scale=bar_size, angle=360-angle,
                 right=x * scene_width,
                 bottom=y * scene_height)
    rbar = C.add('static bar', scale=bar_size, angle=angle,
                 left=lbar.right,
                 bottom=lbar.bottom)
    ball_bottom = rbar.top - (bar_size * sin(angle) - eps) * scene_height
    ball = C.add('dynamic ball', scale=0.1,
                 center_x=x * scene_width,
                 bottom=ball_bottom)

    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING],
    )
    C.set_meta(C.SolutionTier.BALL)
