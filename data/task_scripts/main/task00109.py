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

import phyre.creator as creator_lib
import numpy as np


@creator_lib.define_task_template(
    max_tasks=100,
    wall_height=np.linspace(0.3, 0.6, 4),
    ramp_center=np.linspace(0.2, 0.6, 5),
    ramp_height=np.linspace(0.6, 0.8, 3),
    bar_angle=np.linspace(15., 30., 3),
    ball_size=np.linspace(0.05, 0.1, 2),
    search_params=dict(
        required_flags=['TWO_BALLS:GOOD_STABLE'],
        excluded_flags=['BALL:GOOD_STABLE', 'TWO_BALLS:TRIVIAL'],
        diversify_tier='two_balls',
        max_search_tasks=360,
        ),
    version='10',
)
def build_task(C, wall_height, ramp_center, ramp_height, bar_angle, ball_size):
    # Add ramps
    ramp1 = C.add('static bar', scale=0.3) \
     .set_center_x(ramp_center*C.scene.width) \
     .set_bottom(ramp_height*C.scene.height) \
     .set_angle(-20.)

    ramp2 = C.add('static bar', scale=0.3) \
     .set_angle(bar_angle)\
     .set_right(ramp1.right + 0.15*C.scene.width) \
     .set_top(ramp1.bottom -0.1*C.scene.height)

    ball = C.add('dynamic ball', scale=ball_size) \
     .set_left(ramp1.left) \
     .set_bottom(ramp1.top)

    # Add goal with wall to get ball over
    wall = C.add('static bar', scale=wall_height) \
     .set_center_x(ramp2.left - 0.15*C.scene.width) \
     .set_bottom(0.0) \
     .set_angle(90.)

    goal = C.add('static bar', scale=1.0) \
     .set_left(wall.right) \
     .set_bottom(0.0) \

    # Add a slope to avoid
    slope = C.add('static bar', scale=1.0) \
     .set_angle(-20.) \
     .set_left(ramp2.right +0.05*C.scene.width) \
     .set_top(ramp2.top)

    if (wall.left / C.scene.width < wall.top / C.scene.height or
        (ramp2.bottom / C.scene.height - wall.top / C.scene.height) <
            ball_size):
        raise creator_lib.SkipTemplateParams

    # Create task.
    C.update_task(body1=ball,
                  body2=goal,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
