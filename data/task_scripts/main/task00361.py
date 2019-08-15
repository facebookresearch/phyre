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


def rotate(x, y, radians):
    cos, sin = np.cos(radians), np.sin(radians)
    return x * cos - y * sin, x * sin + y * cos


def bar_from_point_angle(C,
                         x,
                         y,
                         angle,
                         length_x=None,
                         length_y=None,
                         length=None,
                         build=True):
    radians = angle / 180 * np.pi
    if length is None:
        if length_x is not None:
            length = length_x / abs(np.cos(radians))
        elif length_y is not None:
            length = length_y / abs(np.sin(radians))
        else:
            raise ValueError(
                'One of length, length_x, and length_y must be provided')
    endx, endy = rotate(length, 0, radians)
    endx += x
    endy += y
    if not build:
        return None, (endx, endy)
    body = C.add(
        'static bar',
        scale=length / C.scene.width,
        angle=angle,
        center_x=(x + endx) / 2,
        center_y=(y + endy) / 2)
    return body, (endx, endy)


def bar_between_points(C, x, y, endx, endy):
    dx = endx - x
    dy = endy - y
    if dx != 0:
        angle = np.arctan(dy / dx) / np.pi * 180
    else:
        angle = 90

    length = ((x - endx)**2 + (y - endy)**2)**.5
    body = C.add(
        'static bar',
        scale=length / C.scene.width,
        angle=angle,
        center_x=(x + endx) / 2,
        center_y=(y + endy) / 2)
    return body


@creator_lib.define_task_template(
    target_jar_index=range(3),
    first_gap=np.linspace(0.2, 0.3, 3),
    second_gap=np.linspace(0.2, 0.3, 3),
    shelf_angle=np.linspace(-2, 2, 3),
    max_tasks=100,
)
def build_task(C, target_jar_index, shelf_angle, first_gap, second_gap):


    jar3 = C.add('static jar', scale=0.15, right=C.scene.width, bottom=0)

    angle = -10
    start_y = C.scene.height * 0.5
    lens = [first_gap, second_gap, 0.7 - (first_gap + second_gap)]
    gap = (1 - sum(lens)) / 3
    x, y = 0, start_y

    def double_bar(index, x, y):

        bar, _ = bar_from_point_angle(
            C, x, y, angle, length_x=lens[index] * C.scene.width)
        bar.push(20, -20)
        jar = C.add('dynamic jar', scale=0.15, left=bar.right, bottom=0)
        if jar.right >= jar3.left:
            jar.set_right(jar3.left)
        _, (x, y) = bar_from_point_angle(
            C, x, y, angle, length_x=lens[index] * C.scene.width)
        _, (x, y) = bar_from_point_angle(
            C, x, y, angle, length_x=gap * C.scene.width, build=False)
        return x, y, jar

    x, y, jar1 = double_bar(0, x, y)
    first_hole_coords = (x, y)

    x, y, jar2 = double_bar(1, x, y)
    _, (x, y) = bar_from_point_angle(
        C, x, y, angle, length_x=lens[2] * C.scene.width)
    bar_between_points(C, x, y, jar2.right, jar2.top + 4)
    _, (x, y) = bar_from_point_angle(
        C, x, y, angle, length_x=gap * C.scene.width, build=False)

    inro_shelf = bar_between_points(C, 20, 0.85 * C.scene.height,
                                    0.3 * C.scene.width, 0.90 * C.scene.width)
    target_ball = C.add(
        'dynamic ball', scale=0.05, top=C.scene.height, right=inro_shelf.right)

    shelf = C.add(
        'static bar',
        scale=0.1,
        left=first_hole_coords[0],
        top=start_y + 30,
        angle=shelf_angle)
    C.add('dynamic ball', scale=0.08, center_x=shelf.center_x, bottom=shelf.top)

    # Create assignment.
    jar = [jar1, jar2, jar3][target_jar_index]
    C.update_task(
        body1=target_ball,
        body2=jar,
        phantom_vertices=jar.phantom_vertices,
        relationships=[C.SpatialRelationship.INSIDE])
    C.set_meta(C.SolutionTier.GENERAL)
