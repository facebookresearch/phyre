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

"""Template task with a ball that should land on an obstacle bar."""
import phyre.creator as creator_lib

__OBSTACLE_WIDTHS = [val * 0.1 for val in range(2, 8)]
__OBSTACLE_XS = [val * 0.1 for val in range(0, 11)]
__BALL_XS = [val * 0.1 for val in range(2, 9)]


@creator_lib.define_task_template(obstacle_width=__OBSTACLE_WIDTHS,
                                  obstacle_x=__OBSTACLE_XS,
                                  ball_x=__BALL_XS,
                                  max_tasks=100)
def build_task(C, obstacle_width, obstacle_x, ball_x):

    # Add obstacle.
    if obstacle_x + obstacle_width > 1.:
        raise creator_lib.SkipTemplateParams
    obstacle = C.add('static bar', scale=obstacle_width) \
        .set_left(obstacle_x * C.scene.width) \
        .set_bottom(0.5 * C.scene.height)

    # Add ball centered on top of obstacle.
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(ball_x * C.scene.width) \
        .set_bottom(0.9 * C.scene.height)
    if ball.left + ball.width > obstacle.left and ball.right - ball.width < obstacle.right:
        raise creator_lib.SkipTemplateParams

    # Create assignment.
    C.update_task(body1=ball,
                  body2=obstacle,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.SINGLE_OBJECT)
