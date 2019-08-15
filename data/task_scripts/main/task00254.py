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
    seed=range(1000),
    version="2",
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
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(center * scene_width, 0.9 * scene_height)

    top = (ball.bottom - ball.height) / scene_height

    # Create a bunch of stars (y, x).
    stars = []
    #for _ in range(15):
    #    x = (rng.normal() / 6 + 0.5)
    #    y = rng.uniform(0.1, top)
    #    stars.append((x, y))

    angle = 0
    stars = [(center, 0.7)]
    line_length = 1
    n_valid = 0
    while n_valid < 15:
        if line_length >= 3 and rng.uniform() < 0.5:
            # x = rng.uniform()
            # y = rng.uniform(0.1, top)
            x = rng.normal()
            y = rng.normal()
            l = (x * x + y * y) ** .5
            x = x / l * 0.2 + 0.5
            y = y / l * 0.2 + 0.5
            line_length = 1
            angle = rng.uniform() * 2 * np.pi
        else:
            line_length += 1
            step = rng.uniform(0.05, 0.2)
            angle += rng.uniform() * 2 * np.pi / 8
            dx, dy = step * np.cos(angle), step * np.sin(angle)
            x, y = stars[-1]
            x += dx
            y += dy
        stars.append((x, y))
        if  0.0 < x < 1 and 0.0 < y < 1:
            n_valid += 1
    for i, (x, y) in enumerate(stars):
        C.add('static ball', scale=0.05) \
            .set_center(scene_width * x, scene_height * y)


    #x = abs(rng.normal() / 6) + 0.1
    #if ball.center_x < 0.5 * scene_width:
    #    x = 1. - x
    #y = rng.uniform(0.1, top)
    #selected_star = C.add('dynamic ball', scale=0.05) \
    #    .set_center(scene_width * x, scene_height * y)
    #C.add('static bar', scale=0.05) \
    #    .set_center(scene_width * x, scene_height * (y - 0.15))

    # Create task.
    C.update_task(body1=ball,
                  #body2=selected_star,
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
