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

"""Template task in which at least one catapult needs to be fired."""

import phyre.creator as creator_lib

__CATAPULT_XS = [0.1 * val for val in range(2, 9)]
__CATAPULT_YS = [0.1 * val for val in range(0, 7)]


@creator_lib.define_task_template(
    max_tasks=100,
    catapult1_x=__CATAPULT_XS, catapult1_y=__CATAPULT_YS,
    catapult2_x=__CATAPULT_XS, catapult2_y=__CATAPULT_YS,
)
def build_task(C, catapult1_x, catapult1_y, catapult2_x, catapult2_y):

    # Skip cases in which catapults are to close together:
    if catapult1_x + 0.3 >= catapult2_x:
        raise creator_lib.SkipTemplateParams

    # Create catapults with balls.
    ball1 = _make_catapult(C, catapult1_x, catapult1_y, left=True)
    ball2 = _make_catapult(C, catapult2_x, catapult2_y, left=False)

    # Create assignment.
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)


def _make_catapult(C, x, y, left=False):
    """Builds a catapult."""

    # Base of the catapult.
    base = C.add('static bar', scale=0.1) \
            .set_bottom(y * C.scene.height) \
            .set_center_x(x * C.scene.width)
    C.add('static bar', scale=0.02) \
     .set_angle(90.0) \
     .set_bottom(base.top) \
     .set_left(base.left)
    C.add('static bar', scale=0.02) \
     .set_angle(90.0) \
     .set_bottom(base.top) \
     .set_right(base.right)

    # Hinge and top line.
    bar_center_x = base.left + (base.right - base.left) / 2.
    ball = C.add('static ball', scale=0.05) \
            .set_bottom(base.top) \
            .set_center_x(bar_center_x)
    line = C.add('dynamic bar', scale=0.25) \
            .set_center_x(bar_center_x) \
            .set_bottom(ball.top) \
            .set_angle(20.0 if left else -20.0)

    # Ball that needs to move.
    top_ball = C.add('dynamic ball', scale=0.07) \
                .set_bottom(line.top)
    if left:
        top_ball.set_left(line.left)
    else:
        top_ball.set_right(line.right)
    return top_ball
