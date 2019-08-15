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

    # Add two bars that are supposed to touch each other.
    bar1 = C.add('dynamic bar', scale=0.25) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(.3 * scene_width)
    bar2 = C.add('dynamic bar', scale=0.25) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(.7 * scene_width)

    # Add obstacle.
    C.add('static bar', scale=0.6) \
        .set_center_x(0.5 * scene_width) \
        .set_bottom(0.5 * scene_height)

    # Create task.
    C.update_task(body1=bar1,
                  body2=bar2,
                  relationships=[C.SpatialRelationship.TOUCHING])
