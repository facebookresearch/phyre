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

"""Unfinished single-ball task."""
import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    # Create catapults with balls.
    ball1, line1 = _make_catapult(C, 0.5, 0.1)

    C.add(
        'static bar',
        scale=0.4,
        angle=90,
        bottom=line1.top,
        right=line1.center_x + 10)
    C.add(
        'dynamic ball', scale=0.1, bottom=line1.top, right=line1.center_x + 40)
    C.add('static bar', scale=0.4, angle=90, bottom=line1.top, left=line1.right)
    C.add('static bar', scale=0.9, bottom=0, right=C.scene.width)

    C.add('static bar', scale=0.3, angle=90, bottom=0, right=line1.left)

    #ball2 = C.add('static ball', left=b2.right, top=b2.top - 120, scale=0.05)
    # Create assignment.
    C.update_task(
        body1=ball1,
        body2=C.bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])


def _make_catapult(C, x, y):
    """Builds a catapult."""

    # Base of the catapult.

    base = C.add('static standingsticks ', scale=0.1) \
            .set_bottom(y * C.scene.height) \
            .set_center_x(x * C.scene.width)

    # Hinge and top line.
    bar_center_x = base.left + (base.right - base.left) / 2.
    ball = C.add('static ball', scale=0.05) \
            .set_bottom(base.top) \
            .set_center_x(bar_center_x)
    line = C.add_box(height=3, width=120) \
            .set_center_x(bar_center_x) \
            .set_bottom(ball.top)

    # Ball that needs to move.
    top_ball = C.add('dynamic ball', scale=0.04) \
                .set_bottom(line.top)
    top_ball.set_left(line.left)
    return top_ball, line
