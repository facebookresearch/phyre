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

"""Template task with two balls that must touch rather than fall in jars."""
import numpy as np
import phyre.creator as creator_lib

__BALL_SIZE = 0.1


@creator_lib.define_task_template(
    ball1_x=np.linspace(0.1, 0.9, 8),
    ball2_x=np.linspace(0.1, 0.9, 8),
    ball1_y=np.linspace(0.5, 0.8, 8),
    ball2_y=np.linspace(0.5, 0.8, 8),
    version='2',
)
def build_task(C, ball1_x, ball2_x, ball1_y, ball2_y):

    # Do not generate duplicate tasks or very nearby pairs.
    if ball2_x <= ball1_x + .2:
        raise creator_lib.SkipTemplateParams

    # Add balls.
    ball1 = C.add('dynamic ball', scale=__BALL_SIZE) \
             .set_center_x(ball1_x * C.scene.width) \
             .set_bottom(ball1_y * C.scene.height)
    ball2 = C.add('dynamic ball', scale=__BALL_SIZE) \
             .set_center_x(ball2_x * C.scene.width) \
             .set_bottom(ball2_y * C.scene.height)

    # Add jars under the balls.
    C.add('dynamic jar', scale=0.15) \
     .set_center_x(ball1.left + (ball1.right - ball1.left) / 2.) \
     .set_bottom(0.)
    C.add('dynamic jar', scale=0.15) \
     .set_center_x(ball2.left + (ball2.right - ball2.left) / 2.) \
     .set_bottom(0.)

    # Create task.
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
