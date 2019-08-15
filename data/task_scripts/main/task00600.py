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
import numpy as np

__LEFT=np.linspace(0.05, 0.2, 3)
__HEIGHT=np.linspace(0.7, 0.5, 3)
__BLOCKS=range(8,14)
__WIDTH = np.linspace(0.05, 0.2, 4)

@creator_lib.define_task_template(
    left=__LEFT,
    height=__HEIGHT,
    blocks=__BLOCKS,
    base_width=__WIDTH,
    max_tasks=1,
    search_params=dict(max_search_tasks=1),
    version="3"
)
def build_task(C, left, height, blocks, base_width):

    # Create boxes.
    base = C.add('dynamic bar',
        scale=base_width,
        bottom=0,
        left=left*C.scene.width)
    for i in range(blocks):
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

    # Create ball on a slope blocked from falling off
    slope = C.add('static bar',
        scale=0.4,
        bottom=C.scene.height*height,
        angle=8.,
        right=C.scene.width*1.0,
    )
    block = C.add('static bar',
        scale=0.03,
        angle=90.,
        bottom=slope.bottom,
        left=slope.left)
    ball = C.add('dynamic ball', scale=0.1)
    ball.set(left=block.right, bottom=block.top)

    # Create a sloped platform for the ball to land on
    slope2 = C.add('static bar',
        scale=0.6,
        angle=10.,
        bottom=0.3*C.scene.height,
        left=base.right,
    )
    wall = C.add('static bar',
        scale=0.1,
        angle=90.,
        bottom=slope2.bottom,
        left=slope2.left,
    )

    #Prevent large single balls from winning
    guard = C.add('static bar',
        scale=0.15,
        top=C.scene.height,
        angle=90,
        center_x=C.scene.width/2.0)

    # Create task.
    C.update_task(
        body1=ball, body2=base, relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
