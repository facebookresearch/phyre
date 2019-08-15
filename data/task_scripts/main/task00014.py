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


@creator_lib.define_task_template(
    hole_left=np.linspace(0.1, 0.3, 8),
    height=np.linspace(0.3, 0.7, 8),
    ball_size=np.linspace(0.05, 0.15, 5),
    left=[True, False],
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
        max_search_tasks=640,
    ),
    version='4')
def build_task(C, hole_left, height, left, ball_size):
    # Add ball.
    if left:
        ball_center = hole_left
    else:
        ball_center = 1 - hole_left
    ball = C.add(
        'dynamic ball',
        scale=ball_size,
        center_x=ball_center * C.scene.width,
        bottom=height * C.scene.height)

    if left:
        C.add(
            'static bar',
            scale=0.75*hole_left,
            angle=90,
            center_x=ball.right,
            bottom=0
        )
    else:
        C.add(
            'static bar', 
            scale=0.75*hole_left,
            angle=90,
            center_x=ball.left,
            bottom=0
        )

    # Add a vecrtical separator.
    C.add(
        'static bar',
        scale=0.7,
        angle=90,
        left=C.scene.width / 2,
        top=C.scene.height)

    left_floor = C.add('static bar', 0.5, bottom=0, left=0)
    right_floor = C.add('static bar', 0.5, bottom=0, left=left_floor.right)

    target = right_floor if left else left_floor

    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.BALL)
