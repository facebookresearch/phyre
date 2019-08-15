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
__HOLE_LEFT = [0.1 * val for val in range(2, 9) if val != 5]
__BAR_HEIGHT = [0.1 * val for val in range(3, 8)]


@creator_lib.define_task_template(
    max_tasks=100,
    ball_size=__BALL_SIZES,
    hole_size=__HOLE_SIZES,
    hole_left=__HOLE_LEFT,
    bar_height=__BAR_HEIGHT)
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

    # A series of vertical bars.
    for i in range(1, 10):
        x_position = i / 10 * C.scene.width
        if left_bar.right <= x_position <= right_bar.left:
            continue
        bar = C.add(
            'static bar', scale=0.2, angle=90).set(
                center_x=x_position,
                center_y=left_bar.top + 0.05 * (i % 3 - 1) * C.scene.height)
        if bar.top >= ball.bottom - ball.height / 2:
            # If the bar is too high, skip the instance.
            raise creator_lib.SkipTemplateParams

    target = C.left_wall if hole_left > 0.5 else C.right_wall
    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.GENERAL)


def _bar_with_hole(C, bar_height, hole_left, hole_size, angle=0):
    if not 0 < hole_left < 1.0:
        raise creator_lib.SkipTemplateParams

    left_bar = C.add(
        'static bar', scale=hole_left, angle=angle).set(
            left=0, bottom=bar_height * C.scene.height)

    hole_right = hole_left + hole_size
    if not 0 < hole_right < 1.0:
        raise creator_lib.SkipTemplateParams

    right_bar = C.add(
        'static bar', scale=1.0 - hole_right, angle=angle).set(
            right=C.scene.width, bottom=bar_height * C.scene.height)

    return left_bar, right_bar
