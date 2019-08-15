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

    # Set properties of obstacles.
    scene_width = C.scene.width
    scene_height = C.scene.height

    # Add obstacle to scene.
    obstacle = C.add('static bar', scale=0.6) \
        .set_bottom(scene_height * 0.6) \
        .set_left(0.)

    # Add jar.
    jar = C.add('dynamic jar', scale=0.3) \
        .set_bottom(0.) \
        .set_left(scene_width / 2.)
    phantom_vertices = jar.get_phantom_vertices()

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1)
    ball.set(
        left=obstacle.right - ball.width,
        bottom=obstacle.top + C.scene.height // 5)

    # Create task.
    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=phantom_vertices)
