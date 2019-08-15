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

"""Template task with a ball that must not roll of a cliff with two holes."""

import phyre.creator as creator_lib

__BAR_YS = [0.1 * val for val in range(0, 5)]
__BAR_OFFSET = [0.05 * val for val in range(3, 5)]
__BAR_LENGTH = [0.9, 0.95, 1.]
__LEFT = [True, False]


@creator_lib.define_task_template(
    bar_y=__BAR_YS,
    bar_offset=__BAR_OFFSET,
    bar_length=__BAR_LENGTH,
    left=__LEFT)
def build_task(C, bar_y, bar_offset, bar_length, left):

    # Add obstacle bars, one of which has a hole on the side.
    bar_scale = 0.5 * bar_length
    lower_bar = C.add('static bar', scale=bar_scale) \
                 .set_angle(20. if left else -20.) \
                 .set_bottom(bar_y * C.scene.height)
    if left:
        lower_bar.set_right(1.01 * C.scene.width)
    else:
        lower_bar.set_left(-0.01 * C.scene.width)
    upper_bar = C.add('static bar', scale=bar_scale) \
                 .set_angle(-20. if left else 20.) \
                 .set_bottom((bar_y + bar_offset) * C.scene.height)
    if left:
        upper_bar.set_right(lower_bar.left)
    else:
        upper_bar.set_left(lower_bar.right)

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1) \
            .set_bottom(0.9 * C.scene.height)
    if left:
        ball.set_center_x(upper_bar.left)
    else:
        ball.set_center_x(upper_bar.right)

    # Create assignment.
    C.update_task(body1=ball,
                  body2=lower_bar,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
