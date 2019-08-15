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

    # Add static bar.
    bar = C.add('static bar', scale=0.5) \
        .set_left(scene_width / 2.) \
        .set_bottom(scene_width / 2.)

    # Add jar on top of bar.
    cover = C.add('dynamic jar', scale=0.2) \
        .set_angle(180.0) \
        .set_left(scene_width / 2.) \
        .set_bottom(bar.top)

    # Add jar on ground.
    jar = C.add('dynamic jar', scale=0.2) \
        .set_center_x(scene_width / 4.) \
        .set_bottom(0.)
    phantom_vertices = jar.get_phantom_vertices()

    # Add balls.
    C.add('dynamic ball', scale=0.1) \
        .set_center_x(cover.left + cover.width / 2.) \
        .set_bottom(0.9 * scene_height)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(cover.left + cover.width / 2.) \
        .set_bottom(bar.top)

    # create assignment:
    C.update_task(body1=ball,
                  body2=jar,
                  relationships=[C.SpatialRelationship.INSIDE],
                  phantom_vertices=phantom_vertices)
