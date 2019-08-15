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

"""Template task inspired by a simple Goldberg machine."""
import phyre.creator as creator_lib

__BALL_XS = [0.1 * val for val in range(2, 8)]
__BALL_YS = [0.1 * val for val in range(2, 8)]


@creator_lib.define_task_template(
    ball1_x=__BALL_XS,
    ball1_y=__BALL_YS,
    ball2_x=__BALL_XS,
    ball2_y=__BALL_YS,
    search_params=dict(
        require_two_ball_solvable=True,
        diversify_tier='two_balls',
        max_search_tasks=1000,
    ),
    version='3',
)
def build_task(C, ball1_x, ball1_y, ball2_x, ball2_y):

    # Task definition is symmetric.
    if ball2_x - ball1_x < 0.3:
        raise creator_lib.SkipTemplateParams

    # Create ball.
    ball1, vertical_bar1 = _create_structure(C, ball1_x, ball1_y, left=True)
    ball2, vertical_bar2 = _create_structure(C, ball2_x, ball2_y, left=False)

    # Add basket to catch falling balls.
    ramp_scale = (vertical_bar2.left - vertical_bar1.right) / float(2. * C.scene.width)
    C.add('static bar', scale=ramp_scale) \
     .set_angle(-10.) \
     .set_left(vertical_bar1.left) \
     .set_bottom(-0.015 * C.scene.height)
    C.add('static bar', scale=ramp_scale) \
     .set_angle(10.) \
     .set_right(vertical_bar2.right) \
     .set_bottom(-0.015 * C.scene.height)

    # Create assignment.
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)


def _create_structure(C, ball_x, ball_y, left=True):
    """Creates entire Goldberg machine structure."""

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1) \
            .set_center_x(ball_x * C.scene.width) \
            .set_center_y(ball_y * C.scene.height)

    # Add alley in which ball is located.
    bottom_bar = C.add('static bar', scale=0.2) \
                  .set_top(ball.bottom)
    top_bar = C.add('static bar', scale=0.1) \
               .set_bottom(ball.top + 0.01 * C.scene.height)
    if left:
        bottom_bar.set_right(ball.right)
        top_bar.set_right(ball.right)
    else:
        bottom_bar.set_left(ball.left)
        top_bar.set_left(bottom_bar.left)

    # Add stick that can be toppled over.
    stick = C.add('dynamic bar', scale=0.12) \
             .set_angle(90.) \
             .set_bottom(bottom_bar.top)
    if left:
        stick.set_left(bottom_bar.left)
    else:
        stick.set_right(bottom_bar.right)

    # Add downward facing bars.
    vertical_bar = C.add('static bar', scale=1.0) \
                    .set_angle(90.) \
                    .set_top(bottom_bar.top)
    if left:
        vertical_bar.set_right(bottom_bar.right)
    else:
        vertical_bar.set_left(bottom_bar.left)
    
    # Add downward facing bars.
    if left:
        vertical_bar_2 = C.add('static bar', scale=0.1) \
                        .set_bottom(stick.top + 0.2*C.scene.height) \
                        .set_left(stick.left)
    else:
        vertical_bar_2 = C.add('static bar', scale=0.1) \
                        .set_bottom(stick.top + 0.2*C.scene.height) \
                        .set_right(stick.right)

    return ball, vertical_bar
