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

__BASE_Y = [0.05 * val for val in range(0, 10)]
__BASE_X = [0.05 * val for val in range(0, 10)]
__SCALE = [0.35, 0.45, 0.55]


@creator_lib.define_task_template(
    base_y=__BASE_Y,
    base_x=__BASE_X,
    scale=__SCALE,
    search_params=dict(
        require_two_ball_solvable=True,
        diversify_tier='two_balls',
        max_search_tasks=300,
    ),
    version='4',
)
def build_task(C, base_y, base_x, scale):

    # Create base for standing sticks.
    base = C.add('static bar', scale=0.15) \
            .set_center_x((0.25 + base_x) * C.scene.width) \
            .set_bottom(base_y * C.scene.height)
    C.add('static bar', scale=0.02) \
     .set_angle(90.0) \
     .set_left(base.left) \
     .set_bottom(base.top)
    C.add('static bar', scale=0.02) \
     .set_angle(90.0) \
     .set_right(base.right) \
     .set_bottom(base.top)

    # Add standing sticks.
    sticks = C.add('dynamic standingsticks', scale=scale) \
              .set_center_x(base.left + (base.right - base.left) / 2.0) \
              .set_bottom(base.top)
    phantom_vertices = sticks.get_phantom_vertices()

    # Add ball hovering over standing sticks.
    ball = C.add('dynamic ball', scale=0.03) \
            .set_center_x(sticks.left + (sticks.right - sticks.left) / 2.0) \
            .set_top(sticks.top - 0.005 * C.scene.height)

    # Cover sticks with obstacles:
    C.add('static bar', scale=0.15) \
     .set_center_x(ball.left + (ball.right - ball.left) / 2.0) \
     .set_bottom(sticks.top + 0.05 * C.scene.height)
    C.add('dynamic ball', scale=0.03) \
     .set_right(base.left) \
     .set_center_y(sticks.bottom + (sticks.top - sticks.bottom) / 2.0)
    C.add('dynamic ball', scale=0.03) \
     .set_left(base.right) \
     .set_center_y(sticks.bottom + (sticks.top - sticks.bottom) / 2.0)

    # Add bottom wall.
    bottom_wall = C.add('static bar', 1.0, bottom=0.0, left=0.0)

    # Create task.
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING],
        phantom_vertices=phantom_vertices)
    C.set_meta(C.SolutionTier.TWO_BALLS)
