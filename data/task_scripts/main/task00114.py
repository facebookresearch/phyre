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

"""Template task in which two balls should touch each other despite obstacles."""
import numpy as np

import phyre.creator as creator_lib

__BALL_XS = np.linspace(0.15, 0.9, 8)
__BAR_YS = [0.1 * val for val in range(3, 7)]
__OBSTACLE_WIDTH = np.linspace(0.1, 0.4, 6)


@creator_lib.define_task_template(
    ball1_x=__BALL_XS,
    ball2_x=__BALL_XS,
    bar_y=__BAR_YS,
    obstacle_width=__OBSTACLE_WIDTH,
    search_params=dict(
        require_two_ball_solvable=True,
        diversify_tier='two_balls',
        max_search_tasks=1000,
    ),
    version='4')
def build_task(C, ball1_x, ball2_x, bar_y, obstacle_width):

    # Task definition is symmetric.
    if ball2_x <= ball1_x:
        raise creator_lib.SkipTemplateParams

    # Add two balls.
    ball_scale = 0.1
    ball1 = C.add('dynamic ball', scale=ball_scale) \
             .set_center_x(ball1_x * C.scene.width) \
             .set_bottom(0.9 * C.scene.height)
    ball2 = C.add('dynamic ball', scale=ball_scale) \
             .set_center_x(ball2_x * C.scene.width) \
             .set_bottom(0.9 * C.scene.height)
    if (ball2.left - ball1.right) < ball_scale * C.scene.width:
        raise creator_lib.SkipTemplateParams

    # Add obstacles.
    bar_scale = 1. - (ball2.left / float(C.scene.width))
    bar1 = C.add('static bar', scale=bar_scale) \
            .set_bottom(bar_y * C.scene.height) \
            .set_right(C.scene.width)
    bar2 = C.add('static bar', scale=bar_scale + obstacle_width) \
            .set_bottom((bar_y - 0.4 * obstacle_width) * C.scene.height) \
            .set_right(C.scene.width)
    bar_scale = (bar1.top - bar2.top) / float(C.scene.height)
    vertical_bar = C.add('static bar', scale=bar_scale + 0.04) \
                    .set_angle(90.) \
                    .set_left(bar1.left) \
                    .set_bottom(bar2.top)
    C.add('static bar', scale=1.0) \
     .set_angle(90.) \
     .set_top(vertical_bar.top - 0.05 * C.scene.height) \
     .set_left(bar2.left)

    # Obstacle preventing single-ball solutions.
    C.add('static bar', scale=1.0, angle=90.) \
     .set_left(ball2.right + 0.02 * C.scene.width) \
     .set_bottom(bar1.top)

    # Second ball should fall straight down.
    if ball1.left + (ball1.right - ball1.left) / 2. >= bar2.left:
        raise creator_lib.SkipTemplateParams

    # Add ramps.
    ramp_scale = bar2.left / (1.9 * C.scene.width)
    C.add('static bar', scale=ramp_scale, angle=-10.0) \
     .set_left(0.0) \
     .set_bottom(0.0)
    C.add('static bar', scale=ramp_scale, angle=10.0) \
     .set_right(bar2.left) \
     .set_bottom(0.0)

    # Create assignment:
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
