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

SHIFT_RIGHT = np.linspace(0.4, 0.6, 3)
OBSTACLE_ANGLE = np.linspace(-10, 10, 3)

@creator_lib.define_task_template(
    radius=np.linspace(5, 12, 5),
    jar_scale=np.linspace(0.20, 0.30, 4),
    jar_position=np.linspace(0.4, 0.6, 10),
    x_offset=np.linspace(0.0, 0.1, 2),
    angle=np.linspace(45, 60, 5),
    ball_offset=np.linspace(5, 15, 2),
    shift_right=SHIFT_RIGHT,
    obstacle_angle=OBSTACLE_ANGLE,
    search_params=dict(
        max_search_tasks=1000,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball'),
    version='6',
    max_tasks=100,
)
def build_task(C, radius, jar_scale, angle, jar_position, x_offset,
               ball_offset, shift_right, obstacle_angle):

    C.add(
        'static bar',
        angle=-angle,
        bottom=0,
        right=0.2 * C.scene.width)

    C.add(
        'static bar',
        angle=angle,
        bottom=0,
        left=0.8 * C.scene.width)
    
    # Add jar.
    jar = C.add(
        'dynamic jar',
        scale=jar_scale,
        center_x=(jar_position + x_offset) * C.scene.width,
        bottom=0)

    # Add obstacle.
    obstacle = C.add(
        'static bar',
        scale=90 / C.scene.width,
        angle=obstacle_angle,
        center_x=(shift_right + x_offset) * C.scene.width,
        bottom=max(.3 * C.scene.height, jar.top + radius * 4))

    if jar.right > obstacle.right + 10:
        raise creator_lib.SkipTemplateParams

    ball_in_jar = C.add(
        'dynamic ball',
        scale=0.05 + jar_scale / 5,
        center_x=jar.center_x,
        bottom=10)

    # Add ball:
    ball = C.add(
        'dynamic ball',
        scale=radius / C.scene.width * 2,
        left=obstacle.left + ball_offset,
        bottom=obstacle.top + radius)

    # Add task.
    C.update_task(
        body1=ball,
        body2=ball_in_jar,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
