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

import phyre.creator as creator_lib
import numpy as np


@creator_lib.define_task_template(
    bar_y=np.linspace(0.4, 0.7, 10),
    bottom_jar_scale=np.linspace(0.15, 0.20, 3),
    bottom_jar_x=np.linspace(0.25, 0.50, 5),
    left_diag_angle=np.linspace(30, 70, 3),
    right_diag_angle=np.linspace(30, 70, 3),
    max_tasks=100,
    search_params=dict(required_flags=['TWO_BALLS:GOOD_STABLE']),
    version='2'
)
def build_task(C, bar_y, bottom_jar_scale, bottom_jar_x, left_diag_angle,
               right_diag_angle):
    # Add jar on the ground.
    jar = C.add(
        'dynamic jar',
        scale=bottom_jar_scale,
        center_x=C.scene.width * bottom_jar_x,
        bottom=0.)
    ball_in_jar = C.add(
        'dynamic ball',
        scale=0.03 + bottom_jar_scale / 5,
        center_x=jar.center_x,
        bottom=10)

    # Add top bar.
    bar = C.add(
        'static bar',
        scale=0.8 - jar.left / C.scene.width,
        left=jar.left,
        bottom=C.scene.height * bar_y)

    # Add jar on top of bar.
    cover = C.add(
        'dynamic jar',
        scale=0.1,
        angle=180.0,
        left=bar.left,
        top=min(C.scene.height, C.scene.height * bar_y + 150))

    C.add('static bar', scale=0.15, angle=90, right=bar.right, bottom=bar.top)

    ball = C.add(
        'dynamic ball',
        scale=0.05,
        center_x=cover.left + cover.width * 0.5,
        bottom=bar.top)

    C.add(
        'static bar',
        scale=1,
        angle=left_diag_angle,
        bottom=-2,
        left=0.9 * C.scene.width)
    C.add(
        'static bar',
        scale=1,
        angle=-right_diag_angle,
        bottom=-2,
        right=0.1 * C.scene.width)
    # create assignment:
    C.update_task(
        body1=ball,
        body2=ball_in_jar,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
