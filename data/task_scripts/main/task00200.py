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

"""
Template task with a ball that must hit the left or right wall, and a
horizontal bar that is preventing this from happening.
"""
import phyre.creator as creator_lib

__BALL_SIZE = 0.1
__HOLE_SIZE = 0.2
__HOLE_LEFT = [0.1 * val for val in range(3, 7)]
__BAR_HEIGHT = [0.1 * val for val in range(5, 7)]
__LEFT_WALL = [True, False]


@creator_lib.define_task_template(
    hole_left=__HOLE_LEFT,
    bar_height=__BAR_HEIGHT,
    left_wall=__LEFT_WALL)
def build_task(C, hole_left, bar_height, left_wall):

    # Compute right side of hole.
    hole_right = hole_left + __HOLE_SIZE
    if hole_right >= 1.0:
        raise creator_lib.SkipTemplateParams

    # Add ball.
    ball = C.add('dynamic ball', scale=__BALL_SIZE) \
            .set_center_x((hole_left if left_wall else hole_right) * C.scene.width) \
            .set_bottom(0.8 * C.scene.height)

    # Add horizontal bar with hole.
    C.add('static bar', scale=hole_left) \
     .set_left(0) \
     .set_bottom(bar_height * C.scene.height)
    C.add('static bar', scale=1.0 - hole_right) \
     .set_right(C.scene.width) \
     .set_bottom(bar_height * C.scene.height)

    # Add vertical bars that prevent "cheating".
    C.add('static bar', scale=1.0 - bar_height) \
     .set_angle(90.) \
     .set_left(0) \
     .set_bottom(bar_height * C.scene.height)
    C.add('static bar', scale=1.0 - bar_height) \
     .set_angle(90.) \
     .set_right(C.scene.width) \
     .set_bottom(bar_height * C.scene.height)

    C.update_task(
        body1=ball,
        body2=C.left_wall if left_wall else C.right_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
