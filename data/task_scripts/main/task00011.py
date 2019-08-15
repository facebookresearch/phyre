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

"""Template task with a ball that must not roll of a cliff."""
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    bar_y=np.linspace(0.1, 0.5, 10),
    ball_x=np.linspace(0.2, 0.8, 10),
    angle_left=np.linspace(15, 30, 5),
    angle_right=np.linspace(15, 30, 5),
    length_left=np.linspace(0.2, 0.8, 4),
    search_params=dict(
        max_search_tasks=1000,
        required_flags=['BALL:GOOD_STABLE'],
        diversify_tier='ball'
    ),
    version='4')
def build_task(C, bar_y, ball_x, angle_left, angle_right, length_left):

    # Add obstacle bars.
    scene_width = C.scene.width
    scene_height = C.scene.height
    right_bar = C.add('static bar', scale=1-length_left) \
                 .set_angle(angle_left) \
                 .set_bottom(bar_y * scene_height) \
                 .set_right(1.01 * scene_width)
    left_bar = C.add('static bar', scale=length_left) \
                .set_angle(-angle_right) \
                .set_bottom((bar_y + .2) * scene_height) \
                .set_left(-0.01 * scene_width)

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1) \
            .set_center_x(ball_x * scene_width) \
            .set_bottom(0.9 * scene_height)

    if ball.left < left_bar.right and left_bar.top > C.scene.height * 0.9:
        raise creator_lib.SkipTemplateParams

    # Create assignment.
    C.update_task(
        body1=ball,
        body2=right_bar,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
