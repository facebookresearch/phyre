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

    # Create boxes.
    base = C.add('dynamic bar', scale=0.2) \
        .set_bottom(0.) \
        .set_left(.4 * C.scene.width)
    offset = .01 * C.scene.width
    for i in range(8):
        left = C.add('dynamic bar', scale=0.07) \
            .set_angle(90.) \
            .set_bottom(base.top) \
            .set_left(base.left + offset)
        C.add('dynamic bar', scale=0.07) \
            .set_angle(90.) \
            .set_bottom(base.top) \
            .set_right(base.right - offset)
        base = C.add('dynamic bar', scale=0.2) \
            .set_bottom(left.top) \
            .set_left(base.left)
    task_body2 = base

    # Create balls.
    for i in range(1, 3):
        ball = C.add('dynamic ball', scale=0.1)
        ball.set_center(base.left + (i - 1) * 1.5 * ball.width,
                        base.top + i * 1. * ball.width)
        if i == 1:
            task_body1 = ball

    # Create task.
    C.update_task(body1=task_body1,
                  body2=task_body2,
                  relationships=[C.SpatialRelationship.ABOVE])
