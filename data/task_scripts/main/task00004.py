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

"""Task template in which a ball should not fall off a beam balancer."""

import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    bar_y=np.linspace(0.1, 0.6, 12),
    ball_x=np.linspace(0.2, 0.8, 14),
    bar_center=np.linspace(0.25, 0.65, 5),
    bar_scale=np.linspace(0.3, 0.45, 8),
    search_params=dict(
        max_search_tasks=1000,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball'
    ),
    version='8',
)
def build_task(C, bar_y, ball_x, bar_center, bar_scale):

    # Generate static bar.
    scene_width = C.scene.width
    scene_height = C.scene.height
    bar = C.add('static bar', scale=1.0) \
           .set_bottom(bar_y * scene_height) \
           .set_left(0.0)

    # Generate fulcrum and beam.
    fulcrum = C.add(
        'static ball',
        scale=0.1,
        bottom=bar.top,
        center_x=bar_center*scene_width
    )
    beam = C.add('dynamic bar', scale=bar_scale) \
            .set_center_x(bar_center * scene_width) \
            .set_bottom(fulcrum.top)

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1) \
            .set_center_x(ball_x * scene_width) \
            .set_bottom(0.9 * scene_height)
    # Add guards.
    guard_l = C.add('static bar', scale=0.2) \
            .set_angle(90.0) \
            .set_left(beam.left - 0.15*scene_width) \
            .set_top(ball.bottom -  0.15*scene_height)

    guard_r = C.add('static bar', scale=0.2) \
            .set_angle(90.0) \
            .set_right(beam.right + 0.15*scene_width) \
            .set_top(ball.bottom -  0.15*scene_height)
            
    # Ball should be above bar.
    if ball.bottom < bar.top:
        raise creator_lib.SkipTemplateParams
    if ball.right < beam.left or ball.left > beam.right:
        raise creator_lib.SkipTemplateParams

    if guard_l.bottom < bar.top:
         guard_l.set_bottom(bar.top)
         guard_r.set_bottom(bar.top)

    # Create task.
    C.update_task(
        body1=ball,
        body2=beam,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
