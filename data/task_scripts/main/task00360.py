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
    main_first_segment_len=np.linspace(0.15, 0.20, 3),
    main_second_segment_len=np.linspace(0.15, 0.20, 3),
    main_third_segment_len=np.linspace(0.15, 0.20, 3),
    roof_segment_scale=np.linspace(0.02, 0.04, 4),
    center_point=np.linspace(0.4, 0.65, 4),
    right_bar_angle=np.linspace(45, 65, 6),
    distracting_shelf=range(2),
    search_params=dict(required_flags=['BALL:GOOD_STABLE']),
    version='3',
)
def build_task(C, right_bar_angle, center_point, main_first_segment_len,
               main_second_segment_len, main_third_segment_len, roof_segment_scale, distracting_shelf):

    # Vertical stopper.
    stopper = C.add('static bar',
                    scale=0.1,
                    angle=90,
                    left=C.scene.width * (center_point + 0.05) + 2,
                    bottom=0)
    bottom_wall = C.add('static bar', scale=(center_point + 0.07), bottom=0) \
                   .set_left(stopper.right)

    segment_lens = np.array([
        main_first_segment_len, main_second_segment_len, main_third_segment_len, 1
    ])
    hole_size = 0.04
    pushes = [0] + np.cumsum(segment_lens + hole_size).tolist()[:-1]
    for i in range(4):
        C.add(
            'static bar',
            scale=segment_lens[i],
            angle=-right_bar_angle,
            right=C.scene.width * (center_point - 0.05),
            bottom=0).push(-pushes[i] * C.scene.width + 10, 0)
    C.add(
        'static bar',
        scale=2,
        angle=-right_bar_angle,
        right=C.scene.width * (center_point - 0.05),
        bottom=0).push(0, -4)

    bs = []
    for i in range(6):
        step = 30
        bs.append(
            C.add(
                'static bar',
                scale=roof_segment_scale,
                angle=-right_bar_angle,
                left=C.scene.width * (center_point - 0.05),
                bottom=-2).push(-step * i - 60, 50))

    jar = C.add(
        'dynamic jar',
        scale=0.15,
        angle=90 - right_bar_angle,
        right=(center_point - 0.05) * C.scene.width + 25,
        bottom=0)
    while jar.top < C.scene.height * 0.9:
        jar.push(0, 20)
    jar.set_angle(90 - right_bar_angle - 5)

    if jar.left < 3 or jar.top > C.scene.height - 3:
        raise creator_lib.SkipTemplateParams

    ball = C.add(
        'dynamic ball',
        scale=0.05,
        angle=90 - right_bar_angle,
        center_x=jar.center_x,
        center_y=jar.center_y).push(0, -6)

    C.add(
        'dynamic ball',
        scale=0.05,
        angle=90 - right_bar_angle,
        center_x=jar.center_x,
        center_y=jar.center_y).push(0, 8)

    # Distracting ball.
    distracting_ball = C.add(
        'dynamic ball',
        scale=0.05,
        center_x=C.scene.width * 0.75,
        center_y=C.scene.width * 0.75)
    if distracting_shelf:
        C.add('static bar',
              scale=0.03,
              center_x=distracting_ball.center_x,
              top=distracting_ball.bottom - 5)

    # Create assignment.
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_BALL)
