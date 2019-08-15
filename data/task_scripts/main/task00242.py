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
import math


@creator_lib.define_task
def build_task(C):

    # Set properties of objects.
    scene_width = C.scene.width
    scene_height = C.scene.height

    # Create a bunch of stars (y, x).
    stars = [
        # Horizontal "line".
        (.5, .3),
        (.5, .4),
        (.5, .5),
        (.5, .6),
        (.5, .7),
        # Left-hand curve.
        (.05, .05 + math.sqrt(.0)),
        (.13, .05 + math.sqrt(.01)),
        (.25, .05 + math.sqrt(.02)),
        # Right-hand curve.
        (.05, .95 - math.sqrt(.0)),
        (.13, .95 - math.sqrt(.01)),
        (.25, .95 - math.sqrt(.02)),
        # Random other stars.
        (.25, .5),
        (.75, .25),
        (.75, .75),
    ]
    for star in stars:
        C.add('static ball', scale=0.05) \
            .set_center(scene_width * star[1], scene_height * star[0])

    # Create ball.
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(0.5 * scene_width, 0.9 * scene_height)

    # Create task.
    C.update_task(body1=ball,
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
