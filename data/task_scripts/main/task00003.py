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

"""Template task in which the agent should knock a vertical bar against the wall."""
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    jar_x=np.linspace(0.05, 0.95, 20),
    bar_scale=np.linspace(0.2, 0.5, 4),
    jitter_x=np.linspace(-2, 2, 5),
    search_params=dict(required_flags=['BALL:GOOD_STABLE']),
    version='2')
def build_task(C, jar_x, bar_scale, jitter_x):

    # Up side down jar as a vase for the bar.
    vase = C.add(
        'dynamic jar',
        scale=0.1,
        angle=0,
        bottom=0,
        center_x=jar_x * C.scene.width)

    # Add vertical bar.
    bar = C.add(
        'dynamic bar',
        scale=bar_scale,
        angle=90,
        center_x=vase.center_x + jitter_x,
        bottom=4)

    if vase.left <= bar.width or vase.right >= C.scene.width - 1 - bar.width:
        raise creator_lib.SkipTemplateParams

    # Create assignment:
    max_offset = 40
    if bar.height + max_offset > bar.left:
        wall = C.add('static bar', 1.0, left=0, angle=90, bottom=0)
    elif bar.height + max_offset > (C.scene.width - bar.right):
        wall = C.add('static bar', 1.0, right=C.scene.width, angle=90, bottom=0)
    else:
        raise creator_lib.SkipTemplateParams
    C.update_task(
        body1=bar, body2=wall, relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
