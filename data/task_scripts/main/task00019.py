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

"""Template task in which two balls should not touch each other."""
import numpy as np
import phyre.creator as creator_lib

BALL_X = np.linspace(0, 1, 128)

@creator_lib.define_task_template(
    ball_x=BALL_X,
    target_x=BALL_X,
    target_size=np.linspace(0.1, 0.2, 2),
    lower_ball_y=[0.7, 0.5],
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
        max_search_tasks=1000,
    ),
    version='4',
)
def build_task(C, ball_x, target_x, target_size, lower_ball_y):

    # Add two balls.
    ball_scale = 0.1
    ball1 = C.add(
        'dynamic ball',
        scale=ball_scale,
        center_x=ball_x * C.scene.width,
        bottom=0.9 * C.scene.height)
    C.add(
        'dynamic ball',
        scale=ball_scale,
        center_x=ball_x * C.scene.width,
        bottom=lower_ball_y * C.scene.height)
    if ball1.left >= C.scene.width - 3:
        raise creator_lib.SkipTemplateParams

    # Add bottom wall.
    bottom_wall = C.add('static bar', 1.0, left=0., angle=0., bottom=0.)
    target = C.add('static bar', scale=target_size, center_x=target_x * C.scene.width, bottom=bottom_wall.top)
    C.add('static bar', 0.02, right=target.left, angle=90., bottom=target.top)
    C.add('static bar', 0.02, left=target.right, angle=90., bottom=target.top)
    if target.left < ball1.left:
        C.add('static bar', 0.02, right=target.left, angle=90., bottom=target.top)
    else:
        C.add('static bar', 0.02, left=target.right, angle=90., bottom=target.top)

    # Create assignment:
    C.update_task(
        body1=ball1,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
