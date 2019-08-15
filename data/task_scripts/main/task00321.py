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

"""Template task with a ball that must pass through a hole in the ground"""
import numpy as np
import phyre.creator as creator_lib

__BALL_SIZES = [0.1, 0.2]
__HOLE_SIZES = [0.1, 0.2]
__HOLE_LEFT = [0.1 * val for val in range(2, 9)]
__BAR_HEIGHT = [0.1 * val for val in range(3, 8)]


@creator_lib.define_task_template(
    ball_size=np.linspace(0.1, 0.2, 4),
    hole_size=np.linspace(0.1, 0.2, 4),
    hole_left=np.linspace(0.2, 0.8, 16),
    bar_height=np.linspace(0.05, 0.7, 16),
    version='2',
)
def build_task(C, ball_size, hole_size, hole_left, bar_height):
    # Skip if the ball is bigger than the hole
    if ball_size > hole_size:
        raise creator_lib.SkipTemplateParams

    # Add ball
    ball = C.add('dynamic ball', scale=ball_size) \
            .set_center_x(0.5 * C.scene.width) \
            .set_top(0.98 * C.scene.height)
    left_bar = C.add('static bar', scale=hole_left) \
                .set_left(0) \
                .set_bottom(bar_height * C.scene.height)
    if ball.bottom < left_bar.top + 5:
        raise creator_lib.SkipTemplateParams

    hole_right = hole_left + hole_size
    if hole_right >= 1.0:
        raise creator_lib.SkipTemplateParams

    right_bar = C.add('static bar', scale=1.0 - hole_right) \
                .set_right(C.scene.width) \
                .set_bottom(bar_height * C.scene.height)

    # Skip if ball is over the hole.
    if left_bar.right < ball.center_x < right_bar.right:
        raise creator_lib.SkipTemplateParams

    bottom_wall = C.add('static bar', 1.0, left=0, bottom=0)
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.PRE_BALL)
