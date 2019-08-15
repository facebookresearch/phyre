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
    bar_y=np.linspace(0.4, 0.65, 10),
    bottom_jar_scale=np.linspace(0.15, 0.20, 3),
    bottom_jar_x=np.linspace(0.25, 0.50, 5),
    right_diag_angle=np.linspace(30, 70, 3),
    bar_offset=np.linspace(0.1, 0.2, 3),
    max_tasks=100,
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
    ),
    version='2',
)
def build_task(C, bar_y, bottom_jar_scale, bottom_jar_x, right_diag_angle,
               bar_offset):

    scene_width = C.scene.width
    scene_height = C.scene.height

    if bar_y >= 0.6 and bottom_jar_x > 0.4:
        # Hard tasks.
        raise creator_lib.SkipTemplateParams

    # Add jar on ground.
    jar = C.add(
        'dynamic jar',
        scale=bottom_jar_scale,
        center_x=scene_width * bottom_jar_x,
        bottom=0.)
    ball_in_jar = C.add(
        'dynamic ball',
        scale=0.05 + bottom_jar_scale / 8,
        center_x=jar.center_x,
        bottom=10)

    # Add top bar.
    bar = C.add(
        'static bar',
        scale=1.0,
        left=jar.left + bar_offset * C.scene.width,
        bottom=scene_height * bar_y)

    # Add jar on top of bar.
    cover = C.add(
        'dynamic jar', scale=0.12, angle=180.0, left=bar.left, bottom=bar.top)

    ball = C.add(
        'dynamic ball',
        scale=0.05,
        center_x=cover.left + cover.width * 0.5,
        bottom=bar.top)
    if bar.left < 3 * ball.width:
        raise creator_lib.SkipTemplateParams

    C.add(
        'static bar',
        scale=1,
        angle=right_diag_angle,
        bottom=bar.bottom,
        left=max(0.7 * C.scene.width, cover.right + 10))
    # create assignment:
    C.update_task(
        body1=ball,
        body2=ball_in_jar,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
