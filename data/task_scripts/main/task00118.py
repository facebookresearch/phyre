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

"""Template task in which balls need to be rolled out of two jars."""
import phyre.creator as creator_lib
import numpy as np

__CENTER_Y = np.linspace(0.2, 0.7, 5)
__JAR_SIZE = [0.3, 0.35]
__JAR_LEFT = [True, False]

@creator_lib.define_task_template(
    max_tasks=100,
    y1=__CENTER_Y,
    y2=__CENTER_Y,
    j1_size=__JAR_SIZE,
    j2_size=__JAR_SIZE,
    j1_left=__JAR_LEFT,
    j2_left=__JAR_LEFT,
    version="3"
)
def build_task(C, y1, y2, j1_size, j2_size, j1_left, j2_left):
    #Make ground slope into the center
    if j1_left and j1_size == 0.35 or (not j2_left and j2_size == 0.35):
        raise creator_lib.SkipTemplateParams
    C.add('static bar', scale=1.0) \
       .set_angle(15.0) \
       .set_bottom(0.0) \
       .set_left(C.scene.width/2.0)

    C.add('static bar', scale=1.0) \
       .set_angle(-15.0) \
       .set_bottom(0.0) \
       .set_right(C.scene.width/2.0)

    jar1 = C.add('static jar', scale=j1_size) \
           .set_angle(85.0 if j1_left else -85.0) \
           .set_bottom(y1*C.scene.width) \
           .set_center_x(0.25*C.scene.width)

    if j1_left:
        ball1 = C.add('dynamic ball', scale=0.07) \
               .set_bottom(jar1.bottom + 0.02*C.scene.height) \
               .set_left(jar1.left-0.03*C.scene.width)
    else:
        ball1 = C.add('dynamic ball', scale=0.07) \
               .set_bottom(jar1.bottom + 0.02*C.scene.height) \
               .set_right(jar1.right+0.03*C.scene.width)

    jar2 = C.add('static jar', scale=j2_size) \
           .set_angle(85.0 if j2_left else -85.0) \
           .set_bottom(y2*C.scene.width) \
           .set_center_x(0.75*C.scene.width)
    if j2_left:
        ball2 = C.add('dynamic ball', scale=0.07) \
               .set_bottom(jar2.bottom + 0.02*C.scene.height) \
               .set_left(jar2.left-0.03*C.scene.width)
    else:
        ball2 = C.add('dynamic ball', scale=0.07) \
               .set_bottom(jar2.bottom + 0.02*C.scene.height) \
               .set_right(jar2.right+0.03*C.scene.width)
    # Create task.
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
