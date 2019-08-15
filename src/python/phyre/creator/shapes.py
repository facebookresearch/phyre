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

"""Functions to build thrift shape objects.

Each shape is defined by a subclass of ShapeBuilder. To build a shape call
`build` class method. It returns a tuple (list_of_shape, phantom_vertices).

Function get_builders returns a maping for builder names to builders is should
be used by clients instead of direct introspection.
"""
import abc
import math
import numpy as np

from phyre.creator import constants
from phyre.interface.scene import ttypes as scene_if

SCENE_HEIGHT = constants.SCENE_HEIGHT
SCENE_WIDTH = constants.SCENE_WIDTH


def get_builders():
    def yield_subclasses(cls):
        for subcls in cls.__subclasses__():
            yield subcls
            yield from yield_subclasses(subcls)

    return {cls.__name__.lower(): cls for cls in yield_subclasses(ShapeBuilder)}


class ShapeBuilder(object):

    @classmethod
    def default_sizes(cls, scale):
        """Convert single scale parameter to a dict of arguments for build."""
        raise RuntimeError(
            'Using "scale" is not supported for %s' % cls.__name__)

    @classmethod
    @abc.abstractmethod
    def _build(cls, **kwargs):
        """Build the shape with the parameters.

        Returns either
            shape_or_list_shapes
        or tuple
            (shape_or_list_shapes, phantom_vertices).
        """
        pass

    @classmethod
    def build(cls, scale=None, **kwargs):
        """Build the shape either from scale or kwargs.

        Returns tuple (list_of_shapes, phantom_vertices).
        """
        if scale is not None:
            kwargs.update(cls.default_sizes(scale))
        ret = cls._build(**kwargs)
        # Add phantom_vertices if not provided.
        if not isinstance(ret, (tuple, list)):
            ret = ret, None
        elif len(ret) < 2 or isinstance(ret[1], scene_if.Shape):
            ret = ret, None
        # Make sure a list of shapes is returned.
        shapes, phantom_vertices = ret
        if isinstance(shapes, scene_if.Shape):
            shapes = [shapes]
        return shapes, phantom_vertices


def _interpolate(scale_range, scale):
    assert len(scale_range) == 2
    return (1. - scale) * scale_range[0] + scale * scale_range[1]


def vertices_to_polygon(vertices):
    poly_vertices = []
    for v in vertices:
        poly_vertices.append(scene_if.Vector(v[0], v[1]))
    shape = scene_if.Shape(polygon=scene_if.Polygon(vertices=poly_vertices))
    assert is_valid_convex_polygon(poly_vertices)
    return shape


def is_valid_convex_polygon(points):
    # Checks that points form a convex polygon such that the points are in
    # conter clockwise order.
    if len(points) < 3:
        return False
    looped_points = points + points[:2]
    looped_points = [np.array([p.x, p.y]) for p in looped_points]
    for p1, p2, p3 in zip(looped_points, looped_points[1:], looped_points[2:]):
        a = p3 - p2
        b = p1 - p2
        # Exterior product between vector to p3 and vector to p1 must be
        # positive.
        if a[0] * b[1] - a[1] * b[0] <= 0:
            return False
    return True


class Ball(ShapeBuilder):

    @classmethod
    def default_sizes(cls, scale):
        # Map scale and corresponding alpha to radius.
        scale_range = [0., SCENE_WIDTH / 2.]
        radius = _interpolate(scale_range, scale)
        return dict(radius=radius)

    @classmethod
    def _build(cls, radius):
        # Add 0.5 to make rasterization of circles more accurate.
        radius = int(radius) + 0.5
        return scene_if.Shape(circle=scene_if.Circle(radius=radius))


class Box(ShapeBuilder):

    @classmethod
    def default_sizes(cls, scale):
        scale_range = [0., SCENE_WIDTH]
        size = _interpolate(scale_range, scale)
        return dict(height=size, width=size)

    @classmethod
    def _build(cls, width, height):
        vertices = []
        for i in range(4):
            vx = (1 - 2 * (i in (1, 2))) / 2. * width
            vy = (1 - 2 * (i in (2, 3))) / 2. * height
            vertices.append((vx, vy))
        return vertices_to_polygon(vertices)


class Bar(Box):

    @classmethod
    def default_sizes(cls, scale):
        scale_range = [0., SCENE_WIDTH]
        return dict(
            width=_interpolate(scale_range, scale),
            height=SCENE_WIDTH / 50.,
        )


class StandingSticks(ShapeBuilder):

    @classmethod
    def default_sizes(cls, scale):
        scale_range = [0., SCENE_WIDTH]
        return dict(
            angle=77.5,
            width=_interpolate(scale_range, scale),
            height=SCENE_WIDTH / 50.,
        )

    @classmethod
    def _build(cls, angle, width, height):

        # create base bar (top-right, top-left, bottom-left, bottom-right):
        bar = []
        y_offset = 0.0  # this governs how asymmetric the sticks are
        for i in range(4):
            vx = ((1 - 2 * (i in (1, 2))) / 3.) * width
            vy = ((1 - 2 * (i in (2, 3))) / 3. + y_offset) * height
            bar.append((vx, vy))

        # rotate bar to create both sticks:
        shapes = []
        radians = [_angle / 180. * math.pi for _angle in [-angle, angle]]
        for radian in radians:
            rotated_bar = []
            for x, y in bar:
                vx = math.cos(radian) * x - math.sin(radian) * y
                vy = math.cos(radian) * y + math.sin(radian) * x
                rotated_bar.append((vx, vy))
            shapes.append(rotated_bar)

        # construct phantom vertices:
        phantom_vertices = (shapes[1][1], shapes[1][2],
                            shapes[0][3], shapes[0][0],
                            shapes[1][3], shapes[1][0],
                            shapes[0][1], shapes[0][2])

        # return shapes:
        return [vertices_to_polygon(shape) for shape in shapes], phantom_vertices


class Jar(ShapeBuilder):

    @classmethod
    def default_sizes(cls, scale):
        scale_range = [0., SCENE_WIDTH]
        height = _interpolate(scale_range, scale)
        width = height / 1.2
        # Thickness is logarithmical and thickness at scale 0.3 is
        # SCENE_WIDTH / 50.
        thickness = (
            math.log(height) / math.log(0.3 * SCENE_WIDTH) * SCENE_WIDTH / 50)
        return dict(
            height=height,
            width=width,
            thickness=thickness,
            base_width=width * .8,
        )

    @classmethod
    def _build(cls, height, width, thickness, base_width):
        # Create box.
        vertices = []
        for i in range(4):
            vx = (1 - 2 * (i in (1, 2))) / 2. * base_width
            vy = (1 - 2 * (i in (2, 3))) / 2. * thickness
            vertices.append((vx, vy))

        # Compute offsets for jar edge coordinates.
        base = (width - base_width) / 2.
        hypotenuse = math.sqrt(height**2 + base**2)
        cos, sin = base / hypotenuse, height / hypotenuse
        x_delta = thickness * sin
        x_delta_top = thickness / sin
        y_delta = thickness * cos

        # Left tilted edge of jar.
        vertices_left = [
            [-width / 2, height - (thickness / 2)],
            [(-base_width / 2), -(thickness / 2)],
            [(-base_width / 2) + x_delta, y_delta - (thickness / 2)],
            [(-width / 2) + x_delta_top, height - (thickness / 2)],
        ]

        # Right tilted edge.
        vertices_right = [
            [width / 2, height - (thickness / 2)],
            [(width / 2) - x_delta_top, height - (thickness / 2)],
            [(base_width / 2) - x_delta, y_delta - (thickness / 2)],
            [(base_width / 2), -(thickness / 2)],
        ]

        phantom_vertices = (vertices_left[0], vertices_left[1],
                            vertices_right[3], vertices_right[0])
        shapes = [
            vertices_to_polygon(vertices),
            vertices_to_polygon(vertices_left),
            vertices_to_polygon(vertices_right),
        ]

        return shapes, phantom_vertices
