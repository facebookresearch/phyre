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
    version="2",
    search_params=dict(
        max_search_tasks=500,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
    ),
)
def build_task(C, seed):
    rng = np.random.RandomState(seed=seed)

    # Set properties of objects.
    scene_width = C.scene.width
    scene_height = C.scene.height

    # Create ball.
    center = rng.uniform(0.2, 0.5)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(center * scene_width, 0.9 * scene_height)

    top = (ball.bottom - ball.height * 2) / scene_height

    # Create a bunch of stars (y, x).
    stars = []

    def _generate_line(start_x, start_y, base_angle, num_nodes, max_x):
        stars = [(start_x, start_y)]
        for _ in range(num_nodes):
            step = rng.uniform(0.05, 0.17)
            angle = base_angle + rng.normal() * 2 * np.pi / 40
            dx, dy = step * np.cos(angle), step * np.sin(angle)
            x, y = stars[-1]
            x += dx
            y += dy
            if x >= max_x:
                break
            stars.append((x, y))
        return stars

    def to_radians(angle):
        return angle / 180 * np.pi

    stars = []
    for i, y in enumerate(reversed(np.linspace(0.1, top, 4))):
        cont = rng.randint(3, 8)
        angle = to_radians(5)
        new_stars = _generate_line(0, y, angle, cont, 0.8 * scene_width)
        if i % 2:
            new_stars = [(1 - x, y) for x, y in new_stars]
        stars.extend(new_stars)

    for i, (x, y) in enumerate(stars):
        size = 0.04
        if 0 <= x <= 1 and 0 <= y <= 1:
            C.add('static ball',
                  scale=size,
                  center_x=scene_width * x,
                  center_y=scene_height * y)

    bottom_wall = C.add('static bar', 1, bottom=0, left=0)

    # Create task.
    C.update_task(body1=ball,
                  body2=bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
