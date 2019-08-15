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

    scene_width = C.scene.width
    scene_height = C.scene.height

    # Add jar.
    target_jar = C.add('dynamic jar', scale=0.2) \
        .set_center_x(0.25 * scene_width) \
        .set_bottom(0.)
    phantom_vertices = target_jar.get_phantom_vertices()

    # Add small bars.
    bar = C.add('static bar', scale=0.1) \
        .set_left(0.33 * scene_width) \
        .set_bottom(0.25 * scene_height)
    C.add('static bar', scale=0.1) \
        .set_left(0.33 * scene_width + bar.width) \
        .set_bottom(0.25 * scene_height + 4. * bar.height)

    # Add platform.
    platform = C.add('static bar', scale=0.5) \
        .set_left(0.33 * scene_width + 2. * bar.width) \
        .set_bottom(0.25 * scene_height + 8. * bar.height)

    # Add second jar.
    source_jar = C.add('dynamic jar', scale=0.2) \
        .set_bottom(platform.top) \
        .set_left(platform.left)

    # Add ball.
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(source_jar.left + 0.5 * source_jar.width, 0.) \
        .set_bottom(source_jar.bottom + 0.02 * scene_height)

    # Create task.
    C.update_task(
        body1=ball,
        body2=target_jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=phantom_vertices)
