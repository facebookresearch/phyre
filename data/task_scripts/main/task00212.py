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
import phyre.creator as creator_lib

__BALL_SIZES = [0.1, 0.15, 0.2]
__HOLE_SIZES = [0.1, 0.15, 0.2]
__HOLE_LEFT = [0.1 * val for val in range(2, 9)]
__BAR_HEIGHT = [0.1 * val for val in range(1, 8)]


@creator_lib.define_task_template(
    max_tasks=100,
    ball_size=__BALL_SIZES,
    hole_size=__HOLE_SIZES,
    hole_left=__HOLE_LEFT,
    bar_height=__BAR_HEIGHT,
)
def build_task(C, ball_size, hole_size, hole_left, bar_height):
    # Skip if the ball is bigger than the hole
    if ball_size > hole_size:
        raise creator_lib.SkipTemplateParams

    # Add ball
    ball = C.add(
        'dynamic ball', scale=ball_size).set(
            center_x=0.5 * C.scene.width, top=0.95 * C.scene.height)

    # Top bar with a hole.
    left_bar, right_bar = _bar_with_hole(C, bar_height, hole_left, hole_size)

    # Skip if ball is over the hole
    if ball.left >= left_bar.right and ball.right <= right_bar.left:
        raise creator_lib.SkipTemplateParams

    if ball.bottom <= left_bar.top:
        raise creator_lib.SkipTemplateParams

    # Bottom bar with a hole.
    shift = 0.1 if hole_left < 0.5 else -0.1
    bar, _ = _bar_with_hole(C, bar_height - ball_size * 2, hole_left + shift,
                            hole_size)
    if bar.bottom <= (ball.right - ball.left) * 0.5:
        raise creator_lib.SkipTemplateParams

    C.update_task(
        body1=ball,
        body2=C.bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])


def _bar_with_hole(C, bar_height, hole_left, hole_size):
    if not 0 < hole_left < 1.0:
        raise creator_lib.SkipTemplateParams

    left_bar = C.add(
        'static bar', scale=hole_left).set(
            left=0, bottom=bar_height * C.scene.height)

    hole_right = hole_left + hole_size
    if not 0 < hole_right < 1.0:
        raise creator_lib.SkipTemplateParams

    right_bar = C.add(
        'static bar', scale=1.0 - hole_right).set(
            right=C.scene.width, bottom=bar_height * C.scene.height)

    return left_bar, right_bar
