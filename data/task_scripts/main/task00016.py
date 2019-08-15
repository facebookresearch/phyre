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


TARGET_SCALE = 0.1


@creator_lib.define_task_template(
    target_position=np.linspace(0.35, 0.65, 10),
    radius=np.linspace(5, 12, 5),
    buffer=np.linspace(0.0, 0.1, 3),
    angle=np.linspace(30, 50, 6),
    search_params=dict(
        max_search_tasks=900,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
    ),
    version='11',
    max_tasks=100,
)
def build_task(C, target_position, radius, buffer, angle):
    # Build a floor with a small target segment
    floor_left = C.add('static bar',
                       bottom=0,
                       scale=target_position,
                       left=0.0)
    target = C.add('static bar',
                   bottom=0,
                   scale=TARGET_SCALE,
                   left=floor_left.right)
    floor_right = C.add('static bar',
                        bottom=0,
                        scale=1 - TARGET_SCALE - target_position,
                        left=target.right)

    # Some (helpful?) obstacles
    blocker = C.add('static bar', bottom=0, angle=90, scale=0.1, right=target.left)
    base = floor_right
    for _ in range(5):
        plank = C.add('static bar', bottom=base.top, left=base.left, scale=0.1)
        base = plank

    # A ramp for launching the ball
    ramp = C.add(
        'static bar',
        angle=-angle,
        bottom=0.3 * C.scene.height,
        right=blocker.left - 0.1 * C.scene.width)
    launch = C.add(
        'static bar',
        scale=0.1,
        angle=10,
        bottom=ramp.bottom,
        left=ramp.right - 0.02 * C.scene.width)
    shield = C.add(
        'static bar',
        angle=-angle,
        bottom=0.3 * C.scene.height + radius * 6,
        right=blocker.left - 0.1 * C.scene.width)
    

    shield2 = C.add(
        'static bar',
        angle=-angle,
        bottom=0.3 * C.scene.height + radius * 10,
        right=blocker.left - 0.1 * C.scene.width)

    C.add(
        'static bar',
        angle=90.0,
        left=base.left,
        bottom=base.top,
        scale=0.1,
    )

    C.add(
        'static bar',
        angle=-30.0,
        top=shield.bottom + 0.1 * C.scene.height,
        left=launch.right,
        scale=0.5
    )


    # The ball
    ball_center_x = max(
        0.05 * C.scene.width, ramp.left +  0.01 * C.scene.width
    )
    ball_center_x += buffer*C.scene.width
    ball_center_y = (
        ramp.bottom + (ramp.right - ball_center_x) *
        math.tan(angle / 360. * 2. * math.pi)
    )
    
    ball = C.add(
        'dynamic ball',
        scale=radius / C.scene.width * 2,
        center_x=ball_center_x + radius,
        center_y=ball_center_y + radius * 1.7)
    ball2_center_y = (
        ramp.bottom + (ramp.right - (ball.center_x + 4*radius)) *
        math.tan(angle / 360. * 2. * math.pi)
    )
    ball2 = C.add(
        'dynamic ball',
        scale=radius / C.scene.width,
        center_x=ball.center_x + 4*radius,
        center_y=ball2_center_y + radius * 2.6)
    if ball2.right >= launch.left:
         ball2.set_bottom(max(launch.top, ball2.bottom))
        
    if ball.right - ball.left >= target.right - target.left:
        raise creator_lib.SkipTemplateParams

    # Add task
    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
