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

    # set properties of objects:
    scene_width = C.scene.width
    scene_height = C.scene.height
    width = scene_width / 1.5
    height = scene_height / 5.
    thickness = scene_width / 50.

    # add two boxes:
    box1 = C.add_box(thickness, height, dynamic=True) \
        .set_bottom(0.) \
        .set_left(.3 * scene_width)
    box2 = C.add_box(thickness, height, dynamic=True) \
        .set_bottom(0.) \
        .set_left(.7 * scene_width)

    # add static box:
    C.add_box(width, thickness, dynamic=False) \
        .set_bottom(scene_height / 2.) \
        .set_left((scene_width - width) / 2.)

    # create assignment:
    C.update_task(body1=box1, body2=box2,
                  relationships=[C.SpatialRelationship.TOUCHING])
