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

    C.add('dynamic jar', scale=0.6) \
        .set_center_x(scene_width / 2.) \
        .set_bottom(0.)

    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(0.5 * scene_width, 0.9 * scene_height)

    C.update_task(body1=ball,
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
