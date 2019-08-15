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

"""Task in which two balls have to escape a ramp."""
import numpy as np

import phyre.creator as creator_lib


SEED = [0]

@creator_lib.define_task_template(
    max_tasks=100,
    ball_x=np.linspace(0.1, 0.3, 10),
    ball_y=np.linspace(0.3, 0.8, 10),
    diff_y=np.linspace(0.1, 0.3, 10),
    version='2',
)
def build_task(C, ball_x, ball_y, diff_y):

    # Set random seed.
    rng = np.random.RandomState(seed=SEED[0])
    SEED[0] += 1

    # Add balls.
    ball_scale = 0.1
    ball1 = C.add('dynamic ball', scale=ball_scale) \
             .set_center_x(ball_x * C.scene.width) \
             .set_bottom(ball_y * C.scene.height)
    ball2 = C.add('dynamic ball', scale=ball_scale) \
             .set_center_x((1.0 - ball_x) * C.scene.width) \
             .set_bottom(ball_y * C.scene.height)

    # Add ramps.
    start_x1 = 0.0
    start_y1 = ball_y - ball_x - diff_y + 0.1
    ramp1 = _generate_line(rng, start_x1, start_y1, 30.0, 10, ball_x)
    start_x2 = 1.0 - ball_x
    start_y2 = max(y for x, y in ramp1)
    ramp2 = _generate_line(rng, start_x2, start_y2, -30.0, 10, 1.0)
    for ball in ramp1 + ramp2:
        if ball[1] < 0.0:
            raise creator_lib.SkipTemplateParams
        C.add('static ball', scale=0.02) \
         .set_center_x(ball[0] * C.scene.width) \
         .set_center_y(ball[1] * C.scene.height)

    # Add bouncing pillars on floor.
    for left in [True, False]:
        obstacle = C.add('static bar', scale=0.05) \
                    .set_angle(90.0) \
                    .set_bottom(0.0)
        if left:
            obstacle.set_left(ball1.left)
        else:
            obstacle.set_right(ball2.right)

    # Create task.
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)


def _generate_line(rng, start_x, start_y, base_angle, num_nodes, max_x):
    stars = [(start_x, start_y)]
    base_angle = np.deg2rad(base_angle)
    for _ in range(num_nodes):
        step = rng.uniform(0.02, 0.06)
        angle = base_angle + rng.normal() * 2.0 * np.pi / 30.0
        dx, dy = step * np.cos(angle), step * np.sin(angle)
        x, y = stars[-1]
        x += dx
        y += dy
        if x >= max_x:
            stars.append((max_x, y))
            break
        stars.append((x, y))
    return stars
