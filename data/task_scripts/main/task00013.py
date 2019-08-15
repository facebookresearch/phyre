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
    seed=range(300),
    version="4",
    search_params=dict(
        max_search_tasks=300,
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball'
    ),
)
def build_task(C, seed):
    rng = np.random.RandomState(seed=seed)

    # Set properties of objects.
    scene_width = C.scene.width
    scene_height = C.scene.height

    # Create ball.
    center = rng.uniform(0.4, 0.6)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(center * scene_width, 0.9 * scene_height)

    top = (ball.bottom - ball.height * 2) / scene_height

    # Create a bunch of stars (y, x).
    stars = []

    def gen_chain(start_x, start_y):
        angle = rng.uniform() * 2 * np.pi
        angle_diff = rng.uniform() * 2 * np.pi / 10
        stars = [(start_x, start_y)]
        line_length = 1
        n_valid = 0
        max_poitns = rng.randint(15, 30)
        while n_valid < max_poitns:
            if line_length >= 3 and rng.uniform() < 0.2:
                x, y = stars[rng.choice(len(stars))]
                line_length = 1
                angle = rng.uniform() * 2 * np.pi
                angle_diff = rng.uniform() * 2 * np.pi / 10
            else:
                line_length += 1
                step = rng.uniform(0.05, 0.2)
                angle += angle_diff
                dx, dy = step * np.cos(angle), step * np.sin(angle)
                x, y = stars[-1]
                x += dx
                y += dy
            if y >= top:
                continue
            stars.append((x, y))
            if 0.0 < x < 1 and 0.0 < y < 1:
                n_valid += 1
        return stars

    stars = []
    for i in range(2):
        stars.extend(gen_chain(0.2 if i else 0.7, 0.5))

    for i, (x, y) in enumerate(stars):
        if 0 <= x <= 1 and 0 <= y <= 1:
            C.add(
                'static ball',
                scale=0.05,
                center_x=scene_width * x,
                center_y=scene_height * y)

    bottom_wall = C.add('static bar', 1, bottom=0, left=0)

    # Create task.
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
