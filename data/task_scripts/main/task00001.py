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

"""A template task with a ball that should touch left or right wall."""
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    ball_x=np.linspace(0.1, 0.9, 32),
    ball_y=np.linspace(0, 40, 8),
    ball_r=np.linspace(0.05, 0.12, 5),
    left=[True, False],
    version='6',
)
def build_task(C, ball_x, ball_y, ball_r, left):
    target_wall = C.add('static bar', 1.0, left=0, angle=90, bottom=0)
    if not left:
        target_wall.set_right(C.scene.width)

    shelf_size = 0.99 - ball_r * 2
    shelf = C.add('static bar', shelf_size, center_x=C.scene.width / 2, top=20)
    C.add('static bar', 0.2, angle=65, right=shelf.left + 5, top=shelf.top)
    C.add('static bar', 0.2, angle=-65, left=shelf.right - 5, top=shelf.top)

    ball = C.add(
        'dynamic ball',
        ball_r,
        left=ball_x * C.scene.width,
        bottom=ball_y + shelf.top)
    if ball.center_x <= shelf.left or ball.center_x >= shelf.right:
        raise creator_lib.SkipTemplateParams
    if abs(ball.center_x - target_wall.center_x) > C.scene.width * .7:
        raise creator_lib.SkipTemplateParams

    C.update_task(
        body1=ball,
        body2=target_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
