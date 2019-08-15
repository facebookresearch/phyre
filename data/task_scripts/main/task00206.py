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


@creator_lib.define_task
def build_task(C):
    # The solution involves three triangular ramps that direct the ball to
    # the target beam.

    # Set properties of obstacles.
    scene_width = C.scene.width
    scene_height = C.scene.height

    # Add obstacles to the scene.
    C.add('static bar', scale=0.6) \
        .set_bottom(0.5 * scene_height) \
        .set_left(0.)
    C.add('static bar', scale=0.6) \
        .set_bottom(0.7 * scene_height) \
        .set_right(scene_width)
    C.add('static bar', scale=0.7) \
        .set_bottom(0.3 * scene_height) \
        .set_left(0.5 * scene_width)

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(0.5 * scene_width, 0.9 * scene_height)

    # Add beam to knock over.
    beam1 = C.add('dynamic bar', scale=0.2) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(0.8 * scene_width)

    # Add other beam.
    C.add('dynamic bar', scale=0.2) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(0.2 * scene_width)

    # Update task.
    C.update_task(body1=beam1,
                  body2=ball,
                  relationships=[C.SpatialRelationship.TOUCHING])
