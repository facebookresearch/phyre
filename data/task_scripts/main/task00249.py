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

"""Tamplet task with a ball that must pass through a hole."""
import phyre.creator as creator_lib

__HOLE_X = [0.05 * val for val in range(6, 16)]
__HOLE_Y = [0.05 * val for val in range(8, 16)]
__LEFT = [True, False]


@creator_lib.define_task_template(
    max_tasks=100, hole_x=__HOLE_X, hole_y=__HOLE_Y, left=__LEFT)
def build_task(C, hole_x, hole_y, left):

    # Add obstacle bars.
    y_offset = 0.15 if left else -0.15
    right_bar = C.add('static bar', scale=hole_x + 0.02) \
                 .set_angle(-20.) \
                 .set_top((hole_y - y_offset) * C.scene.height) \
                 .set_right(1.01 * C.scene.width)
    left_bar = C.add('static bar', scale=1.0 - hole_x + 0.02) \
                .set_angle(20.) \
                .set_top((hole_y + y_offset) * C.scene.height) \
                .set_left(-0.01 * C.scene.width)

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1) \
            .set_bottom(0.9 * C.scene.height)
    center_x = left_bar.right - 0.01 * C.scene.width if left \
        else right_bar.left + 0.01 * C.scene.width
    ball.set_center_x(center_x)

    # Add jar.
    jar = C.add('dynamic jar', scale=0.2, center_x=center_x, bottom=0.0)

    # create assignment.
    C.update_task(body1=ball,
                  body2=jar,
                  relationships=[C.SpatialRelationship.INSIDE],
                  phantom_vertices=jar.phantom_vertices)
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
