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

import math
import numpy as np
import phyre.creator as creator_lib


def sin(x):
    return math.sin(math.radians(x))


def cos(x):
    return math.cos(math.radians(x))


@creator_lib.define_task_template(
    fulcrum_x=np.linspace(0.2, 0.4, 10),
    beam_angle=np.linspace(15, 30, 10),
    beam_size=np.linspace(0.35, 0.5, 10),
    version='2',
    search_params=dict(
        require_two_ball_solvable=True,
        diversify_tier='two_balls',
    ),
)
def build_task(C, fulcrum_x, beam_angle, beam_size):
    scene_width = C.scene.width
    scene_height = C.scene.height

    target_y = 0.6
    target = C.add('static bar',
                   scale=(1.0 - target_y),
                   bottom=target_y * scene_height,
                   right=scene_width, angle=90)
    C.add('static bar',
          scale=0.25,
          bottom=target_y * scene_height,
          right=scene_width, angle=-10)

    # Generate fulcrum and beam.
    fulcrum_scale = 0.10
    fulcrum = C.add('static ball', scale=fulcrum_scale,
                    bottom=0, center_x=fulcrum_x * scene_width)

    offset = 0.5 * beam_size * sin(beam_angle) * scene_height
    beam = C.add('dynamic bar', scale=beam_size, angle=beam_angle,
                 center_x=fulcrum_x * scene_width,
                 bottom=fulcrum.top - offset)
    if beam.left < 0 or beam.bottom < 0:
        raise creator_lib.SkipTemplateParams

    ball_x = (fulcrum_x + 0.5 * beam_size * cos(beam_angle)) * scene_width
    ball = C.add('dynamic ball', scale=0.1,
                 center_x=ball_x,
                 bottom=beam.top)

    C.update_task(
        body1=ball,
        body2=target,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
