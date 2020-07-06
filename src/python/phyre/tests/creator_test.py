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

import math
import random
import unittest

import phyre.creator.creator
import phyre.creator.constants
import phyre.creator.shapes


class TaskCreatorTestCase(unittest.TestCase):
    """Tests creation of bodies in the scene."""

    def test_add_body_functions(self):

        # Loop over all valid objects.
        random.seed(0)
        builders = phyre.creator.shapes.get_builders()
        for dynamic in phyre.creator.constants.DYNAMIC_VALUES:
            color_ids = (phyre.creator.constants.DYNAMIC_COLOR_IDS
                         if dynamic == 'dynamic' else
                         phyre.creator.constants.STATIC_COLOR_IDS)
            for color_id in color_ids:
                color = phyre.creator.constants.color_to_name(color_id)
                for object_type in phyre.creator.constants.FACTORY_OBJECT_TYPES:
                    # Create task with single object.
                    scale = max(0.02, random.random())
                    C = phyre.creator.creator.TaskCreator()
                    C.add('%s %s %s' % (dynamic, color, object_type),
                          scale=scale)
                    self.assertEqual(len(C.body_list), 5)  # Four walls.
                    body = C.body_list[-1]
                    self.assertEqual(body.dynamic, dynamic == 'dynamic')
                    self.assertEqual(body.color, color)
                    self.assertEqual(body.object_type, object_type)
                    self.assertEqual(body._thrift_body.shapeType,
                                     builders[object_type].SHAPE_TYPE)
                    target_diameter = builders[object_type].diameter(scale)
                    self.assertEqual(body._thrift_body.diameter,
                                     target_diameter)

    def test_object_types_reachable(self):
        for name in phyre.creator.shapes.get_builders():
            self.assertIn(name, phyre.creator.constants.FACTORY_OBJECT_TYPES)

    def test_color_consistency(self):
        self.assertEqual(
            sorted(phyre.creator.constants.ROLE_TO_COLOR_ID.values()),
            sorted(range(phyre.creator.constants.NUM_COLORS)))

    def test_add_polygon(self):
        vertices = [(0., 0.), (1., 0.), (2., 2.), (0., 1.)]
        C = phyre.creator.creator.TaskCreator()
        C.add_convex_polygon(vertices, dynamic=True)

    def test_add_multipolygon(self):
        vertices1 = [(0., 0.), (1., 0.), (2., 2.), (0., 1.)]
        vertices2 = [(0., 0.), (5., 0.), (5., 2.), (0., 1.)]
        C = phyre.creator.creator.TaskCreator()
        C.add_multipolygons([vertices1, vertices2], dynamic=True)


class ShapesTest(unittest.TestCase):

    def test_polygon_diameter(self):
        vertices = [(0., 0.), (1., 0.), (2., 2.), (0., 1.)]
        shape = phyre.creator.shapes.vertices_to_polygon(vertices)
        diameter = phyre.creator.shapes.compute_shape_diameter(shape)
        self.assertAlmostEqual(diameter, (2**2 + 2**2)**0.5)

    def test_rectange_centroid(self):
        N = 4
        vertices = []
        for i in range(N):
            angle = math.pi * 2 * i / N
            vertices.append([math.cos(angle), math.sin(angle)])
        print(vertices)
        centroid, _ = phyre.creator.shapes.compute_polygon_centroid(vertices)
        self.assertAlmostEqual(centroid[0], 0.)
        self.assertAlmostEqual(centroid[1], 0.)

    def test_polygon_centroid(self):
        N = 24
        vertices = []
        for i in range(N):
            angle = math.pi * 2 * i / N
            vertices.append([math.cos(angle), math.sin(angle)])
        print(vertices)
        centroid, _ = phyre.creator.shapes.compute_polygon_centroid(vertices)
        self.assertAlmostEqual(centroid[0], 0.)
        self.assertAlmostEqual(centroid[1], 0.)


if __name__ == '__main__':
    unittest.main()
