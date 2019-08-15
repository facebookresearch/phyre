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


@creator_lib.define_task_template(
    seed=range(1),
    version="3",
)
def build_task(C, seed):
    rng = np.random.RandomState(seed=seed)

    # Set properties of objects.
    scene_width = C.scene.width
    scene_height = C.scene.height

    # Create ball.
    center = rng.uniform(0.2, 0.8)
    ball = C.add('dynamic ball', scale=0.07) \
        .set_center(center * scene_width, 0.93 * scene_height)

    top = (ball.bottom - ball.height * 2) / scene_height

    def to_radians(angle):
        return angle / 180 * np.pi

    points = []
    cnt = rng.randint(3, 4)
    for i, y in enumerate(reversed(np.linspace(0.35, top, cnt))):
        scale = rng.uniform(0.15, 0.35)
        #x = points[rng.choice(len(points))]
        if points:
            x, *points = points
        else:
            x = center * scene_width
        x += rng.uniform() * 0.0
        y = (y + rng.normal() * 0.001) * scene_height
        dynamic = rng.uniform() < 0.0
        if dynamic and i != 0:
            C.add('dynamic bar', scale=scale).set_center(x, y)
        else:
            bar = C.add('static bar', scale=scale).set_center(x, y)
            if rng.uniform() < 0.5:
                points.append(bar.left)
                points.append(bar.right)
            else:
                points.append(bar.right)
                points.append(bar.left)
            if rng.uniform() < 0.5:
                C.add('static bar', scale=0.01, right=bar.right, top=bar.top + 2)
            if rng.uniform() < 0.5:
                C.add('static bar', scale=0.01, left=bar.left, top=bar.top + 2)


    x = bar.left if rng.uniform() < 0.5 else bar.right
    target_jar = C.add('dynamic jar', scale=0.2) \
        .set_center_x(x) \
        .set_bottom(0.)
    if target_jar.left < 5 or scene_width - target_jar.right < 5:
        raise creator_lib.SkipTemplateParams
    phantom_vertices = target_jar.get_phantom_vertices()

    # Create task.
    C.update_task(
        body1=ball,
        body2=target_jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=phantom_vertices)
