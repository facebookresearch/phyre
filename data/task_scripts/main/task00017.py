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
import phyre.creator as creator_lib



@creator_lib.define_task_template(
    bar_height=np.linspace(0.2, 0.5, 5),
    bar_x=np.linspace(0.2, 0.8, 5),
    ball_size=np.linspace(0.05, 0.25, 5),
    ramp_size=np.linspace(0.05, 0.2, 5),
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
    ),
    version='2',
)
def build_task(C, bar_height, bar_x, ball_size, ramp_size):
    scene_width = C.scene.width
    scene_height = C.scene.height

    target = C.add('static bar', scale=1.0, left=0, bottom=0)
    bar = C.add('dynamic bar', angle=90, scale=bar_height,
                center_x=bar_x * scene_width, bottom=target.top)

    ball = C.add('dynamic ball', scale=ball_size, bottom=bar.top,
                 center_x=bar.center_x)

    eps = 0.01 * scene_height

    ramp_angle = 45
    ceil = C.add('static bar', scale=1.0, left=0, bottom=ball.top + eps)
    lramp = C.add('static bar', angle=360 - ramp_angle, scale=ramp_size,
                  left=0, bottom=target.top)
    rramp = C.add('static bar', angle=ramp_angle, scale=ramp_size,
                  right=scene_width, bottom=target.top)

    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING],
    )
    C.set_meta(C.SolutionTier.BALL)
