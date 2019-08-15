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
Template task with a ball that must be pushed of an obstacle without knocking
over a ladder.
"""

import phyre.creator as creator_lib

__BALL_Y = [0.1 * val for val in range(5, 9)]
__LADDER_X = [0.1 * val for val in range(2, 8)]
__LADDER_HEIGHT = [val for val in range(3, 7)]


@creator_lib.define_task_template(
    ball_y=__BALL_Y,
    ladder_x=__LADDER_X,
    ladder_height=__LADDER_HEIGHT,
)
def build_task(C, ball_y, ladder_x, ladder_height):

    # Add ladder.
    step_height = 0.07
    ladder_width = 0.15
    base = C.add('dynamic bar', scale=ladder_width) \
            .set_bottom(0.) \
            .set_left(ladder_x * C.scene.width)
    offset = .01 * C.scene.width
    for _ in range(ladder_height):
        left = C.add('dynamic bar', scale=step_height) \
                .set_angle(90.) \
                .set_bottom(base.top) \
                .set_left(base.left + offset)
        C.add('dynamic bar', scale=step_height) \
         .set_angle(90.) \
         .set_bottom(base.top) \
         .set_right(base.right - offset)
        base = C.add('dynamic bar', scale=ladder_width) \
                .set_bottom(left.top) \
                .set_left(base.left)

    # Add falling ball.
    ball =C.add('dynamic ball', scale=0.15) \
     .set_bottom((ball_y + 0.02) * C.scene.height) \
     .set_center_x(base.right)

    if ball.bottom < base.top + 5:
        raise creator_lib.SkipTemplateParams

    # Add reference marker.
    reference = C.add('static bar', scale=0.02) \
                 .set_top(base.bottom)
    if ladder_x <= 0.5:
        reference.set_left(0.0)
    else:
        reference.set_right(C.scene.width)

    # Create task.
    C.update_task(
        body1=base,
        body2=reference,
        relationships=[C.SpatialRelationship.ABOVE])
    C.set_meta(C.SolutionTier.PRE_BALL)
