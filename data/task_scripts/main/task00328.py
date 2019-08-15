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
Template task with a ball that must pass through a hole in the ground, and
a second ball that is trying to prevent this from happening.
"""
import numpy as np
import phyre.creator as creator_lib

__BALL_SIZE = 0.1
__HOLE_SIZE = 0.1


@creator_lib.define_task_template(
    hole_left=np.linspace(0.2, 0.8, 10),
    bar_height=np.linspace(0.2, 0.8, 10),
    confounder=[True, False],
    version='3',
)
def build_task(C, hole_left, bar_height, confounder):

    # Compute right side of hole.
    hole_right = hole_left + __HOLE_SIZE
    if hole_right >= 1.0:
        raise creator_lib.SkipTemplateParams

    # Add balls.
    ball1 = C.add('dynamic ball', scale=__BALL_SIZE) \
             .set_center_x(0.5 * C.scene.width) \
             .set_bottom(0.8 * C.scene.height)
    ball2 = C.add('dynamic ball', scale=__BALL_SIZE) \
             .set_center_x((hole_left if confounder else hole_right) * C.scene.width) \
             .set_bottom(0.7 * C.scene.height)

    # Add bars with hole.
    bar = C.add('static bar', scale=hole_left) \
     .set_left(0) \
     .set_bottom(bar_height * C.scene.height)
    C.add('static bar', scale=1.0 - hole_right) \
     .set_right(C.scene.width) \
     .set_bottom(bar_height * C.scene.height)

    if ball1.top >= bar.top and ball1.bottom <= bar.bottom:
        raise creator_lib.SkipTemplateParams
    if ball2.top >= bar.top and ball2.bottom <= bar.bottom:
        raise creator_lib.SkipTemplateParams

    # Create task.
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_BALL)
