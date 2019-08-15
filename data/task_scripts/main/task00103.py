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

__BALL_SIZE = 0.1
__BAR_X = np.linspace(0.1, 0.4, 7)
__BOTTOM_Y = np.linspace(0.0, 0.5, 7)


@creator_lib.define_task_template(
    hole_left=__BAR_X,
    hole_right=__BAR_X,
    bottom=__BOTTOM_Y,
    search_params=dict(
        max_search_tasks=350,
        required_flags=['TWO_BALLS:GOOD_STABLE'],
        excluded_flags=['TWO_BALLS:TRIVIAL', 'BALL:GOOD_STABLE'],
        diversify_tier='two_balls'),
    version='4')
def build_task(C, hole_left, hole_right, bottom):
    # Add balls.
    height_left, height_right = 0.9, 0.9
    ball1 = C.add(
        'dynamic ball',
        scale=__BALL_SIZE,
        center_x=hole_left * C.scene.width,
        bottom=height_left * C.scene.height)
    ball2 = C.add(
        'dynamic ball',
        scale=__BALL_SIZE,
        center_x=(1 - hole_right) * C.scene.width,
        bottom=height_right * C.scene.height)

    # Add bottom plateau.
    plateau = C.add('static bar', scale=1.0, left=0.0)
    plateau.set_top(bottom * C.scene.height)

    # Add small bars.
    bar1 = C.add('static bar', scale=0.1, angle=90, bottom=plateau.top, center_x=ball1.right)
    bar2 = C.add('static bar', scale=0.1, angle=90, bottom=plateau.top, center_x=ball2.left)

    # Add a vertical separator in the middle.
    C.add(
        'static bar',
        scale=1.0 - bottom - 0.1,
        angle=90,
        left=bar1.left + (bar2.left - bar1.left) / 2.,
        top=C.scene.height)

    # Create task.
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
