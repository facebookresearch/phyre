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
import math
import phyre.creator as creator_lib


def sin(x):
    return math.sin(math.radians(x))


def cos(x):
    return math.cos(math.radians(x))


def tan(x):
    return math.tan(math.radians(x))


@creator_lib.define_task_template(
    hole_height=np.linspace(0.25, 0.5, 5),
    ball_radius=np.linspace(0.025, 0.05, 5),
    theta1=np.linspace(5, 10, 5),
    theta2=np.linspace(30, 40, 5),
    version='2',
)
def build_task(C, hole_height, ball_radius, theta1, theta2):
    scene_width = C.scene.width
    scene_height = C.scene.height

    bar_thickness = 0.02
    hole_size = 0.2
    # hole_height = 0.6
    # ball_radius = 0.05
    ball_x = 0.3  # 0.2 to 0.3
    # theta1 = 10

    target = C.add('static bar', scale=1.0, left=0, bottom=0)
    ramp_scale = (1 - hole_size - bar_thickness * sin(theta1)) / cos(theta1)
    ramp = C.add('static bar', angle=theta1,
                 scale=ramp_scale,
                 right=scene_width,
                 bottom=hole_height * scene_height)

    ball_dy = (1 - ball_x - ball_radius * sin(theta1)) * tan(theta1)
    ball_bottom = ramp.top - scene_height * ball_dy
    ball = C.add('dynamic ball', scale=2 * ball_radius,
                 center_x=ball_x * scene_width,
                 bottom=ball_bottom)

    bar_length = 0.8
    # theta2 = 40
    cx = ball.center_x / scene_width
    cy = ball.center_y / scene_height
    y1 = ball_radius / cos(theta2)
    y2 = (cx - bar_thickness * sin(theta2)) * tan(theta2)
    bar_bottom = cy + y1 - y2

    bar = C.add('dynamic bar', scale=bar_length, angle=theta2,
                left=0,
                bottom=scene_height * bar_bottom)

    if bar.bottom < target.top:
        raise creator_lib.SkipTemplateParams

    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING],
    )
    C.set_meta(C.SolutionTier.PRE_BALL)
