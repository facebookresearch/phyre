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
    column_center=np.linspace(0.3, 0.7, 10),
    column_width=np.linspace(0.1, 0.25, 10),
    lbar_height=np.linspace(0.2, 0.5, 10),
    rbar_height=np.linspace(0.2, 0.5, 10),
    version='1',
    search_params=dict(
        reject_ball_solvable=True,
        require_two_ball_solvable=True,
    ),
)
def build_task(C, column_center, column_width, lbar_height, rbar_height):
    scene_width = C.scene.width
    scene_height = C.scene.height

    column_height = 0.6
    gap = 0.06
    target = C.add('static bar',
                   scale=column_width,
                   bottom=0,
                   center_x=column_center * scene_width)

    lspace = column_center - column_width
    rspace = column_center + column_width
    if lspace < column_width / 2 or rspace < column_width / 2:
        raise creator_lib.SkipTemplateParams
    if abs(rbar_height - lbar_height) < column_width:
        raise creator_lib.SkipTemplateParams

    ball = C.add('dynamic ball', scale=0.1,
                 center_x=column_center * scene_width,
                 top=scene_height)

    left_wall_bot = C.add('static bar', angle=90,
                          scale=lbar_height,
                          bottom=0,
                          right=target.left)
    right_wall_bot = C.add('static bar', angle=90,
                           scale=rbar_height,
                           bottom=0,
                           left=target.right)
    right_wall_top = C.add('static bar', angle=90,
                           scale=column_height - rbar_height - gap,
                           bottom=right_wall_bot.top + gap * scene_height,
                           left=target.right)
    left_wall_top = C.add('static bar', angle=90,
                          scale=column_height - lbar_height - gap,
                          bottom=left_wall_bot.top + gap * scene_height,
                          right=target.left)

    rbar = C.add('dynamic bar', scale=2*column_width,
                 left=left_wall_bot.right,
                 bottom=right_wall_bot.top)
    rfoot = C.add('static bar', scale=0.02,
                  left=left_wall_top.right,
                  top=rbar.bottom)

    lbar = C.add('dynamic bar', scale=2*column_width,
                 right=right_wall_bot.left,
                 bottom=left_wall_bot.top)
    lfoot = C.add('static bar', scale=0.02,
                  right=right_wall_top.left,
                  top=lbar.bottom)

    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)