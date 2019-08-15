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
    bar_y=range(10),
    vbar_x_scale=np.linspace(0.5, 0.6, 4),
    angle=np.linspace(10, 45, 5),
    distance_to_wall=np.linspace(0.01, 0.05, 2),
    version='3',
)
def build_task(C, bar_y, vbar_x_scale, distance_to_wall, angle):

    vbar_x = vbar_x_scale * C.scene.width
    # Add ball on the left.
    ball = C.add(
        'dynamic ball',
        scale=0.08,
        right=vbar_x - 1,
        bottom=0.9 * C.scene.height)

    # Add diagonal bars.
    bars = []
    for i in range(10):
        bar = C.add(
            'static bar',
            scale=0.3,
            angle=-angle,
            bottom=(i * 0.15) * C.scene.height,
            right=ball.left - 2 - distance_to_wall * C.scene.height)
        if bar.bottom > 0:
            bars.append(bar)
    ball.set_left(bars[0].right + 1)

    # Add a vertical separator with a hole.
    if bar_y >= len(bars):
        raise creator_lib.SkipTemplateParams
    hole_top = bars[bar_y].bottom / C.scene.height - distance_to_wall
    if not 0.2 < hole_top < 0.9:
        raise creator_lib.SkipTemplateParams
    hole_size = ball.width / C.scene.width * 2
    C.add(
        'static bar',
        scale=1.0 - hole_top,
        angle=90,
        left=vbar_x,
        top=C.scene.height)
    C.add(
        'static bar',
        scale=hole_top - hole_size,
        angle=90,
        left=vbar_x,
        bottom=0)

    # Add a ball on the right of the separator.
    ball2_bottom = 0.9 if hole_top < 0.7 else 0.3
    C.add(
        'dynamic ball',
        scale=0.1,
        left=vbar_x + 8,
        bottom=ball2_bottom * C.scene.height)

    bottom_wall = C.add('static bar', 1, bottom=0, left=vbar_x + 4)

    # Create assignment.
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
