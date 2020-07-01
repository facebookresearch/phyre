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
from typing import Sequence, Tuple
import math

from phyre.creator import constants
from phyre.creator import shapes as shapes_lib
from phyre.interface.scene import ttypes as scene_if
from phyre.interface.task import ttypes as task_if


class TaskCreator(object):
    """Core object that creates tasks."""

    SpatialRelationship = task_if.SpatialRelationship
    SolutionTier = constants.SolutionTier

    def __init__(self):

        # Create empty scene and task.
        self.scene = scene_if.Scene(bodies=[])
        self.scene.width = constants.SCENE_WIDTH
        self.scene.height = constants.SCENE_HEIGHT
        self.task = task_if.Task(scene=self.scene,
                                 bodyId1=-1,
                                 bodyId2=-1,
                                 relationships=[self.SpatialRelationship.NONE],
                                 phantomShape=None)
        self.set_meta(self.SolutionTier.GENERAL)
        self.body_list = []

        # Build the bounding walls.
        self.bottom_wall = self._add_wall('bottom')
        self.left_wall = self._add_wall('left')
        self.top_wall = self._add_wall('top')
        self.right_wall = self._add_wall('right')

    def _add_wall(self, side):
        # Set wall properties.
        thickness = 5.
        if side == 'left' or side == 'right':
            height = constants.SCENE_HEIGHT
            width = thickness
        else:
            height = thickness
            width = constants.SCENE_WIDTH

        body = self.add_box(dynamic=False, height=height, width=width)
        body.set_color(
            _role_to_color_name('STATIC')).set_object_type(f'{side}-wall')

        if side == 'bottom':
            body.set_left(0).set_top(0)
        elif side == 'left':
            body.set_right(0).set_bottom(0)
        elif side == 'top':
            body.set_left(0).set_bottom(self.scene.height)
        elif side == 'right':
            body.set_left(self.scene.width).set_bottom(0)
        else:
            raise ValueError('Unknown wall side: %s' % side)
        return body

    def add(self, string_arg, scale=0.5, **set_kwargs):
        """Adds body based on description like 'static red box' and a scale."""

        # Parse string and check arguments.
        args = string_arg.split()
        if len(args) not in (2, 3):
            raise ValueError(
                f'Expected body descriton string to be in format'
                ' "dynamic"|"static" [<color>] <shape>. Got: {string_arg}')
        if len(args) == 3:
            dynamic_static, color, shape = args
        else:
            dynamic_static, shape = args
            color = None
        builders = shapes_lib.get_builders()
        assert dynamic_static in constants.DYNAMIC_VALUES, dynamic_static
        assert shape in builders, shape

        # Create and register body.
        if shape == 'bar':
            assert 0 <= scale, ('Bar scale should be non-negattive. Got %s' %
                                scale)
        else:
            assert 0 <= scale <= 1, ('Scale should be between 0 and 1. Got %s' %
                                     scale)
        body = self._add_body_from_builder(
            builders[shape],
            shape,
            dynamic=(dynamic_static == 'dynamic'),
            scale=scale)
        if color is not None:
            body.set_color(color)
        body.set(**set_kwargs)
        return body

    def add_convex_polygon(self,
                           vertices: Sequence[Tuple[float, float]],
                           dynamic: bool = True):
        # Make sure the center mass is at zero. That makes rendering more precise.

        (center_x, center_y), _ = shapes_lib.compute_polygon_centroid(vertices)
        vertices = [(x - center_x, y - center_y) for x, y in vertices]
        shape = shapes_lib.vertices_to_polygon(vertices)
        diameter = shapes_lib.compute_shape_diameter(shape)
        body = Body([shape],
                    dynamic,
                    object_type='poly',
                    diameter=diameter,
                    phantom_vertices=None)
        body._thrift_body.position.x = center_x
        body._thrift_body.position.y = center_y

        self.scene.bodies.append(body._thrift_body)
        self.body_list.append(body)
        return body

    def add_multipolygons(self,
                          polygons: Sequence[Sequence[Tuple[float, float]]],
                          dynamic: bool = True):
        """Adds a union of convex polygons."""
        # Make sure the center mass is at zero. That makes rendering more precise.
        (center_x,
         center_y), _ = shapes_lib.compute_union_of_polygons_centroid(polygons)
        shapes = []
        for vertices in polygons:
            vertices = [(x - center_x, y - center_y) for x, y in vertices]
            shapes.append(shapes_lib.vertices_to_polygon(vertices))
        # TODO(akhti): fix diameter calculation.
        diameter = shapes_lib.compute_shape_diameter(shapes[0])
        body = Body(shapes,
                    dynamic,
                    object_type='compound',
                    diameter=diameter,
                    phantom_vertices=None)

        body._thrift_body.position.x = center_x
        body._thrift_body.position.y = center_y

        self.scene.bodies.append(body._thrift_body)
        self.body_list.append(body)
        return body

    def add_default_box(self, scale, dynamic=True):
        return self._add_body_from_builder(shapes_lib.Box,
                                           'box',
                                           dynamic,
                                           scale=scale)

    def add_default_ball(self, scale, dynamic=True):
        return self._add_body_from_builder(shapes_lib.Ball,
                                           'ball',
                                           dynamic,
                                           scale=scale)

    def add_default_jar(self, scale, dynamic=True):
        return self._add_body_from_builder(shapes_lib.Jar,
                                           'jar',
                                           dynamic,
                                           scale=scale)

    def add_default_bar(self, scale, dynamic=False):
        return self._add_body_from_builder(shapes_lib.Bar,
                                           'bar',
                                           dynamic,
                                           scale=scale)

    def add_box(self, width, height, dynamic=True):
        return self._add_body_from_builder(shapes_lib.Box,
                                           'box',
                                           dynamic,
                                           width=width,
                                           height=height)

    def add_ball(self, radius, dynamic=True):
        return self._add_body_from_builder(shapes_lib.Ball,
                                           'ball',
                                           dynamic,
                                           radius=radius)

    def add_jar(self,
                base_width=50,
                width=50,
                height=100,
                thickness=10,
                dynamic=True):
        return self._add_body_from_builder(shapes_lib.Jar,
                                           'jar',
                                           dynamic,
                                           base_width=base_width,
                                           width=width,
                                           height=height,
                                           thickness=thickness)

    def _add_body_from_builder(self, builder, body_type, dynamic,
                               **builder_kwargs):
        """Create and add new Body object given a ShapeBuider and its params."""
        shapes, phantom_vertices = builder.build(**builder_kwargs)
        diameter = builder.diameter(**builder_kwargs)
        body = Body(shapes, dynamic, body_type, diameter, phantom_vertices)
        # FIXME(akhti): get rid of scene.bodies vs body_list duplication.
        self.scene.bodies.append(body._thrift_body)
        self.body_list.append(body)
        return body

    def _recolor_objects(self, task_body1, task_body2):
        """Change colors so that task bodies are highlighted."""
        for body in self.body_list:
            if 'wall' in body.object_type:
                body.set_color(_role_to_color_name('STATIC'))
            elif body.dynamic:
                if body == task_body1:
                    body.set_color(_role_to_color_name('DYNAMIC_OBJECT'))
                elif body == task_body2:
                    body.set_color(_role_to_color_name('DYNAMIC_SUBJECT'))
                else:
                    body.set_color(_role_to_color_name('DYNAMIC'))
            else:
                if body in (task_body1, task_body2):
                    body.set_color(_role_to_color_name('STATIC_OBJECT'))
                else:
                    body.set_color(_role_to_color_name('STATIC'))

    def update_task(self,
                    body1,
                    body2,
                    relationships,
                    phantom_vertices=None,
                    description=None):

        assert body1.dynamic or body2.dynamic, (
            'At least one dynamic body needed.')
        assert len(relationships) == 1, 'Not supported'
        if relationships[0] == self.SpatialRelationship.LEFT_OF:
            relationships = [self.SpatialRelationship.RIGHT_OF]
            body1, body2 = body2, body1

        self.task.relationships = relationships
        self.task.bodyId1 = self.body_list.index(body1)
        self.task.bodyId2 = self.body_list.index(body2)

        # Add phantom vertices.
        if phantom_vertices is not None:
            poly_vertices = []
            for v in phantom_vertices:
                poly_vertices.append(scene_if.Vector(v[0], v[1]))
            shape = scene_if.Shape(polygon=scene_if.Polygon(
                vertices=poly_vertices))
            self.task.phantomShape = shape

        if description is None:
            self._recolor_objects(body1, body2)
            # Add description.
            relation_name = (self.SpatialRelationship._VALUES_TO_NAMES[
                relationships[0]].lower())
            description = 'Make sure the %s is %s the %s.' % (
                (body1.description, relation_name, body2.description))
            # Check that task description is unambiguous.
            for task_body in ['bodyId1', 'bodyId2']:
                reference_body = self.body_list[getattr(self.task, task_body)]
                for body in self.body_list:
                    if body != reference_body:
                        assert body.description != reference_body.description, (
                            'Ambiguous body description: %s' % body.description)
        self.task.description = description

    def set_meta(self, tier):
        if not isinstance(tier, self.SolutionTier):
            if not isinstance(tier, str):
                raise ValueError(
                    'Expected tier to be either string or SolutionTier')
            tier = getattr(self.SolutionTier, tier)
        self.task.tier = tier.name

    def check_task(self):
        if self.task.tier in ('BALL', 'TWO_BALLS', 'RAMP'):
            body1 = self.body_list[self.task.bodyId1]
            body2 = self.body_list[self.task.bodyId2]
            if 'wall' in body1.object_type or 'wall' in body2.object_type:
                raise ValueError(
                    'Cannot use wall for tiers BALL, TWO_BALLS, and RAMP.')
            if self.task.relationships[0] != (
                    self.SpatialRelationship.TOUCHING):
                raise ValueError('Cannot use anything but TOUCHING'
                                 ' for tiers BALL, TWO_BALLS, and RAMP.')
            for body in self.body_list:
                if "wall" not in body.object_type and not body._thrift_body.shapeType:
                    raise ValueError('All bodies must have a defined shape'
                                     ' for tiers BALL, TWO_BALLS, and RAMP.'
                                     f' Bad object type: {body.object_type}')

        # Check that all polygons are convex.
        for body in self.task.scene.bodies:
            for shape in body.shapes:
                if shape.polygon:
                    assert shapes_lib.is_valid_convex_polygon(
                        shape.polygon.vertices), ('Invalid shape: %s' % body)


class Body(object):
    """A wrapper about scene::Body with a lot of syntax sugar.

    Methods in the class simplify relative positioning of objects and creating
    of multi-shape bodies. Most of the setter methods return the object and so
    could be chaned. For instance,

        ball = Body(...).set_color('red').set_top(0)
        box = Body(...).set_color('blue').set_bottom(ball.top + 10)
        box2 = Body(...).set(color='blue', bottom=ball.top + 10)

    Body also carries meta information about object type, that doesn't exist
    in the interface file (only high level object type data is stored). The
    field is used to refer to objects in tasks. If the value is not None,
    it must present in OBJECT_TYPES list.

    The user generally does not instantiate this object directly.
    """

    def __init__(self,
                 shapes,
                 dynamic,
                 object_type,
                 diameter=None,
                 phantom_vertices=None):
        # Create Thrift body.
        x = y = 0.0
        body = scene_if.Body(
            position=scene_if.Vector(x, y),
            angle=0.,
            shapes=shapes,
        )
        assert dynamic in [True, False]
        body.bodyType = (scene_if.BodyType.DYNAMIC
                         if dynamic else scene_if.BodyType.STATIC)

        if diameter is not None:
            body.diameter = diameter
        self.phantom_vertices = phantom_vertices

        # Set all class variables.
        self._thrift_body = body
        self._scene = None
        self.dynamic = dynamic
        color = (_role_to_color_name('DYNAMIC')
                 if dynamic else _role_to_color_name('STATIC'))
        self.set_object_type(object_type)
        self.set_color(color)

    def get_phantom_vertices(self):
        return self.phantom_vertices

    def set(self, **attributes):
        order = ('angle', 'left', 'right', 'top', 'bottom', 'center_x',
                 'center_y', 'color')
        for name in order:
            if name in attributes:
                getattr(self, 'set_' + name)(attributes.pop(name))
        assert not attributes, 'Unknown attributes'
        return self

    def set_object_type(self, object_type):
        self.object_type = object_type
        if object_type is None:
            return self
        if object_type not in constants.ALL_OBJECT_TYPES:
            raise ValueError(f'Unknown object type: {object_type}')
        if object_type in constants.FACTORY_OBJECT_TYPES:
            shape_type = shapes_lib.get_builders()[object_type].SHAPE_TYPE
            if shape_type:
                self._thrift_body.shapeType = shape_type
        return self

    def _yield_coordinates(self):
        x = self._thrift_body.position.x
        y = self._thrift_body.position.y

        def _to_absolute(rel_x, rel_y, radians):
            rel_x, rel_y = _rotate(rel_x, rel_y, radians)
            return rel_x + x, rel_y + y

        for shape in self._thrift_body.shapes:
            if shape.circle:
                r = shape.circle.radius
                yield _to_absolute(r, r, radians=0)
                yield _to_absolute(-r, -r, radians=0)
            else:
                assert shape.polygon
                for v in shape.polygon.vertices:
                    yield _to_absolute(v.x,
                                       v.y,
                                       radians=self._thrift_body.angle)

    def push(self, x, y):
        """Apply the shift vector in the system of the body's coordinates."""
        x, y = _rotate(x, y, self._thrift_body.angle)
        self._thrift_body.position.x += x
        self._thrift_body.position.y += y
        return self

    def set_center(self, x, y):
        return self.set_center_x(x).set_center_y(y)

    def set_center_x(self, x):
        self.set_left(x - self.width / 2.)
        return self

    def set_center_y(self, y):
        self.set_bottom(y - self.height / 2.)
        return self

    def set_top(self, new_value):
        self._thrift_body.position.y += (new_value - self.top)
        return self

    def set_bottom(self, new_value):
        self._thrift_body.position.y += (new_value - self.bottom)
        return self

    def set_left(self, new_value):
        self._thrift_body.position.x += (new_value - self.left)
        return self

    def set_right(self, new_value):
        self._thrift_body.position.x += (new_value - self.right)
        return self

    def set_angle(self, angle):
        self._thrift_body.angle = angle / 180. * math.pi
        return self

    def set_color(self, color):
        color_id = constants.color_to_id(color)
        if self.dynamic:
            assert color_id in constants.DYNAMIC_COLOR_IDS, (
                f'Color {color} is not allowed for dynamic bodies.')
        else:
            assert color_id in constants.STATIC_COLOR_IDS, (
                f'Color {color} is not allowed for static bodies.')
        self.color = color
        self._thrift_body.color = color_id
        return self

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.top - self.bottom

    @property
    def center_x(self):
        return (self.left + self.right) / 2

    @property
    def center_y(self):
        return (self.top + self.bottom) / 2

    @property
    def right(self):
        return max(x for x, y in self._yield_coordinates())

    @property
    def left(self):
        return min(x for x, y in self._yield_coordinates())

    @property
    def top(self):
        return max(y for x, y in self._yield_coordinates())

    @property
    def bottom(self):
        return min(y for x, y in self._yield_coordinates())

    @property
    def description(self):
        if 'wall' in self.object_type:
            return self.object_type.replace('-', ' ')
        return f'{self.color} {self.object_type}'


def _rotate(x, y, radians):
    cos, sin = math.cos(radians), math.sin(radians)
    return x * cos - y * sin, x * sin + y * cos


def _role_to_color_name(role: str) -> str:
    return constants.color_to_name(constants.ROLE_TO_COLOR_ID[role])
