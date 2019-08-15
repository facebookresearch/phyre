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

import numpy as np

import phyre.creator as creator_lib

__CENTER_XS = np.linspace(0.3, 0.7, 10) #[0.05 * val for val in range(6, 16)]
__CENTER_YS = np.linspace(0.3, 0.7, 10) #[0.05 * val for val in range(6, 14)]


@creator_lib.define_task_template(
    center1_x=__CENTER_XS,
    center1_y=__CENTER_YS,
    center2_x=__CENTER_XS,
    center2_y=__CENTER_YS,
    search_params=dict(
        max_search_tasks=1000,
        required_flags=['TWO_BALLS:GOOD_STABLE'],
        excluded_flags=['TWO_BALLS:TRIVIAL', 'BALL:GOOD_STABLE'],
        diversify_tier='two_balls',
    ),
    version='2')
def build_task(C, center1_x, center1_y, center2_x, center2_y):

    # Task definition is symmetric.
    if center2_x - center1_x <= 0.35:
        raise creator_lib.SkipTemplateParams

    # Add upside-down jar with ball inside.
    center1_x, center1_y = center1_x * C.scene.width, center1_y * C.scene.height
    center2_x, center2_y = center2_x * C.scene.width, center2_y * C.scene.height
    ball1, blocker1 = _create_element(C, center1_x, center1_y, left=True)
    ball2, blocker2 = _create_element(C, center2_x, center2_y, left=False)

    # Add basket to catch falling balls.
    scale = 0.52
    C.add('static bar', scale=scale, angle=-10., bottom=0., left=-0.01 * C.scene.width)
    C.add('static bar', scale=scale, angle=10., bottom=0., right=C.scene.width)
    
    # Add some bars to cut off popular solutions
    C.add('static bar', scale=0.3, bottom=blocker1.top + 0.1*C.scene.height, right=blocker1.left)
    C.add('static bar', scale=0.3, bottom=blocker2.top + 0.1*C.scene.height, left=blocker2.right)

    # Create task.
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)


def _create_element(C, center_x, center_y, left=True):

    # Add tilted static bars.
    angle = -30. if left else 30.
    bottom_bar = C.add('static bar',
                       scale=0.25,
                       angle=angle,
                       center_x=center_x,
                       center_y=center_y)
    top = C.add('static bar',
          scale=0.25,
          angle=angle,
          center_x=center_x,
          center_y=center_y + 0.18 * C.scene.height)
    blocker = C.add('static bar',
                    scale=0.06,
                    angle=90.,
                    bottom=bottom_bar.bottom)
    if left:
        blocker.set_left(bottom_bar.right - 0.02 * C.scene.width)
    else:
        blocker.set_right(bottom_bar.left + 0.02 * C.scene.width)

    # Add ball.
    ball = C.add('dynamic ball',
                 scale=0.1,
                 bottom=blocker.top)
    if left:
        ball.set_right(blocker.left + 0.02 * C.scene.width)
    else:
        ball.set_left(blocker.right - 0.02 * C.scene.width)

    # Add dynamic bar that can move balls.
    handle = C.add('dynamic bar',
                   scale=0.25,
                   angle=angle,
                   center_y=center_y + 0.08 * C.scene.height)
    if left:
        handle.set_right(ball.left)
    else:
        handle.set_left(ball.right)
    return ball, top
