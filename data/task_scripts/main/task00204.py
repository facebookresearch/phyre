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
    base_width = 0.1
    base = C.add('dynamic bar', scale=base_width).set(bottom=0, left=5)
    for i in range(5):
        left = C.add(
            'dynamic bar',
            scale=1 / 32,
            angle=90,
            bottom=base.top,
            left=base.left)
        C.add(
            'dynamic bar',
            scale=1 / 32,
            angle=90,
            bottom=base.top,
            right=base.right)
        base = C.add(
            'dynamic bar', scale=base_width, bottom=left.top, left=base.left)

    # Create ball.
    ball = C.add('dynamic ball', scale=0.1)
    ball.set(left=ball.width / 2, bottom=base.top + 20)

    # Create task.
    C.update_task(
        body1=ball, body2=base, relationships=[C.SpatialRelationship.LEFT_OF])
