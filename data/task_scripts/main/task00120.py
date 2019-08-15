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

import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    seed=range(1000),
    version='3',
    search_params=dict(
        max_search_tasks=1000,
        reject_ball_solvable=True,
        require_two_ball_solvable=True,
    ),
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

    points = []
    cnt = rng.randint(6, 9)
    for i, y in enumerate(reversed(np.linspace(0.15, top, cnt))):
        skip = rng.uniform() < 0.2
        if skip:
            continue

        scale = rng.uniform(0.15, 0.35)
        #x = points[rng.choice(len(points))]
        if points:
            x, *points = points
        else:
            x = center * scene_width
        x += rng.uniform() * 0.0
        y = (y + rng.normal() * 0.02) * scene_height
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
            C.add('static bar', scale=0.01, right=bar.right, top=bar.top + 2)
            C.add('static bar', scale=0.01, left=bar.left, top=bar.top + 2)

    left_trap = C.add('static bar', scale=0.15, angle=10, left=0, bottom=-2)
    right_trap = C.add(
        'static bar', scale=0.15, angle=-10, right=scene_width, bottom=-2)

    bottom_wall = C.add(
        'static bar', (right_trap.left - left_trap.right) / C.scene.width,
        bottom=0,
        center_x=C.scene.width / 2)

    # Create task.
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)