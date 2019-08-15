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

"""Template task in which the agent should knock a bar off an obstacle."""
import numpy as np
import phyre.creator as creator_lib

__OBSTACLE_XS = np.linspace(0, 1, 64)
__OBSTACLE_WIDTHS = np.linspace(0.4, 0.6, 4)
__BAR_SCALES = np.linspace(0.2, 0.3, 2)
__PLATFORM_Y = np.linspace(0.2, 0.5, 5)


@creator_lib.define_task_template(
    obstacle_width=__OBSTACLE_WIDTHS,
    obstacle_x=__OBSTACLE_XS,
    bar_scale=__BAR_SCALES,
    platform_y=__PLATFORM_Y,
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
        max_search_tasks=1000,
    ),
    version='4',
)
def build_task(C, obstacle_width, obstacle_x, bar_scale, platform_y):

    # Add obstacle.
    if obstacle_x + obstacle_width > 1.:
        raise creator_lib.SkipTemplateParams
    obstacle = C.add('static bar', scale=obstacle_width) \
        .set_left(obstacle_x * C.scene.width) \
        .set_bottom(platform_y * C.scene.height)

    # Add vertical bar.
    bar = C.add('dynamic bar', scale=bar_scale) \
        .set_angle(90.) \
        .set_bottom(obstacle.top)
    if obstacle.left > C.scene.width - obstacle.right:
        bar.set_left(obstacle.left)
    else:
        bar.set_right(obstacle.right)

    bottom_wall = C.add('static bar', 1, bottom=0, left=0)
    top_wall = C.add('static bar', 1, bottom=bar.top + 0.2 * C.scene.height, left=0)
    # Create assignment:
    C.update_task(
        body1=bar,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
