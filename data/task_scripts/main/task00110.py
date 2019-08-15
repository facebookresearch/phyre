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

"""Template tasks in which two balls need to be pushed off their platforms."""

import phyre.creator as creator_lib

__STEP_SIZE = 0.1
__PLATFORM_X = [__STEP_SIZE * val for val in range(1, 9)]
__PLATFORM_Y = [__STEP_SIZE * val for val in range(4, 8)]


@creator_lib.define_task_template(
    platform1_x=__PLATFORM_X,
    platform1_y=__PLATFORM_Y,
    platform2_x=__PLATFORM_X,
    platform2_y=__PLATFORM_Y,
    peak_on_left=[True, False],
    version='3',
)
def build_task(C, platform1_x, platform1_y, platform2_x, platform2_y,
               peak_on_left):

    # There should be space on both sides of the platforms.
    if platform2_x - platform1_x <= 2.5 * __STEP_SIZE:
        raise creator_lib.SkipTemplateParams

    # Add two platforms.
    platform1 = C.add('static bar', scale=0.1) \
                 .set_left(platform1_x * C.scene.width) \
                 .set_bottom(platform1_y * C.scene.height)
    platform2 = C.add('static bar', scale=0.1) \
                 .set_left(platform2_x * C.scene.width) \
                 .set_bottom(platform2_y * C.scene.height)

    # Add two balls on top.
    ball1 = C.add('dynamic ball', scale=0.1) \
             .set_center_x(platform1.left + (platform1.right - platform1.left) / 2.) \
             .set_bottom(platform1.top)
    ball2 = C.add('dynamic ball', scale=0.1) \
             .set_center_x(platform2.left + (platform2.right - platform2.left) / 2.) \
             .set_bottom(platform2.top)

    # Add blocker in the middle.
    sep = C.add('static bar', scale=1.0 - min(platform1_y, platform2_y)) \
     .set_angle(90.) \
     .set_top(C.scene.height) \
     .set_center_x(platform1.right + (platform2.left - platform1.right) / 2.)

    peak_x = platform1.center_x if peak_on_left else platform2.center_x
    C.add('static bar', 1.0, angle=5, right=peak_x + 2, top=20)
    C.add('static bar', 1.0, angle=180 - 5, left=peak_x - 2, top=20)
    if peak_on_left:
        hole_size = sep.left - platform1.right
    else:
        hole_size = platform2.left - sep.right
    if hole_size < ball1.width + 2:
        raise creator_lib.SkipTemplateParams

    # Create task.
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
