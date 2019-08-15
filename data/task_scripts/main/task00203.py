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
    # This is a beam balancing task. It is relatively easy. There are two
    # tested solutions:
    #
    # 1) Draw an object under the left side fo the beam to prop it up
    # 2) Draw a counter-balance that lands on the right side of the beam

    scene_width = C.scene.width
    fulcrum = C.add('static ball', scale=0.1)
    radius = fulcrum.width / 2
    fulcrum.set_left(scene_width / 2. - radius) \
        .set_bottom(0.)
    beam = C.add('dynamic bar', scale=0.35) \
        .set_center_x(scene_width / 2.) \
        .set_bottom(radius * 2.)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_left(beam.left) \
        .set_bottom(beam.top)

    # Test against the fulcrum top, not the beam top otherwise it's very hard
    # to solve (the beam many rotate a little bit causing it's top to be higher
    # than the bottom of the blue ball).
    C.update_task(body1=ball,
                  body2=fulcrum,
                  relationships=[C.SpatialRelationship.ABOVE])
