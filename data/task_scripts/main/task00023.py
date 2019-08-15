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

hole_size = 0.2
bar_scale = (1. - hole_size) / 2
top_bar_scale = 0.6
max_balls = 4


@creator_lib.define_task_template(
    step_diff=np.linspace(-0.3, 0.3, 10),
    step_base=np.linspace(0.01, 0.1, 2),
    jar_scale=np.linspace(0.15, 0.3, 3),
    jar_right=np.linspace(0.9, 0.98, 3),
    jar_angle=np.linspace(-10, 10, 13),
    left_side = np.linspace(0.05, 0.2, 5),
    search_params=dict(
        max_search_tasks=1000,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball'
    ),
    max_tasks=100,
    version='3',
)
def build_task(C, step_diff, step_base, jar_scale, jar_right, jar_angle, left_side):
    if step_diff > 0:
        left_step_height_scale = step_base
        right_step_height_scale = left_step_height_scale + step_diff
    else:
        right_step_height_scale = step_base
        left_step_height_scale = right_step_height_scale - step_diff

    if jar_scale < 0.19:
        if abs(step_diff) > 0.19:
            raise creator_lib.SkipTemplateParams
    if jar_scale > 0.26:
        if abs(step_diff) < 0.19:
            raise creator_lib.SkipTemplateParams
        if step_diff < -0.19:
            raise creator_lib.SkipTemplateParams

    left_step = C.add(
        'static bar',
        scale=0.3,
        bottom=left_step_height_scale * C.scene.height,
        left=left_side * C.scene.width)
    pivot_ball = C.add(
        'dynamic ball', scale=0.15, bottom=left_step.top, left=left_step.left)

    bar = C.add('dynamic bar', scale=0.4, bottom=pivot_ball.top, left=5)
    ball = C.add(
        'dynamic ball', scale=0.05, bottom=bar.top, left=0.02 * C.scene.width)

    # Add popular solution blocker
    C.add('static ball', scale=0.1, top=C.scene.height, center_x=pivot_ball.center_x)
    right_step = C.add(
        'static bar',
        scale=0.3,
        angle=jar_angle,
        bottom=right_step_height_scale * C.scene.height,
        right=C.scene.width)
    jar = C.add(
        'dynamic jar',
        scale=jar_scale,
        bottom=right_step.top,
        right=C.scene.width * jar_right)
    ball_in_jar = C.add(
        'dynamic ball',
        scale=0.05 + jar_scale / 8,
        center_x=jar.center_x,
        bottom=jar.bottom + 10)

    C.update_task(
        body1=ball,
        body2=ball_in_jar,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
