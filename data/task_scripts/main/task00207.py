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

"""A simpler version of task 18."""
import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    scene_width = C.scene.width

    radius = 5

    # Add jar.
    jar = C.add(
        'dynamic jar',
        scale=2 / 1.2 * 4 * radius / scene_width,
        center_x=0.5 * scene_width,
        bottom=0)

    # Add obstacle.
    obstacle = C.add(
        'static bar',
        scale=90 / scene_width,
        center_x=0.5 * scene_width,
        bottom=jar.top + radius * 4)

    # Add ball:
    ball = C.add(
        'dynamic ball',
        scale=radius / scene_width * 2,
        left=obstacle.left + 10,
        bottom=obstacle.top + radius)

    # Add task.
    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=jar.phantom_vertices)
