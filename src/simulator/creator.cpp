// Copyright (c) Facebook, Inc. and its affiliates.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
#include "creator.h"

#include <vector>

#include "gen-cpp/scene_types.h"
#include "task_utils.h"

bool cmpIntVector(const ::scene::IntVector& a, const ::scene::IntVector& b) {
  if (a.x < b.x) {
    return true;
  }
  return a.x == b.x && a.y < b.y;
}

::scene::Vector getVector(float x, float y) {
  ::scene::Vector v;
  v.__set_x(x);
  v.__set_y(y);
  return v;
}

::scene::IntVector getIntVector(int x, int y) {
  ::scene::IntVector v;
  v.__set_x(x);
  v.__set_y(y);
  return v;
}

::scene::Body buildBox(float x, float y, float width, float height, float angle,
                       bool dynamic) {
  std::vector<::scene::Vector> vertices;
  for (int i = 0; i < 4; i++) {
    vertices.push_back(getVector((0. + (i == 1 || i == 2)) * width,
                                 (0. + (i == 2 || i == 3)) * height));
  }
  return buildPolygon(x, y, vertices, angle, dynamic);
}

::scene::Body buildCircle(float x, float y, float radius, bool dynamic) {
  ::scene::Body body;
  body.__set_position(getVector(x, y));
  ::scene::Circle circle;
  circle.__set_radius(radius);
  ::scene::Shape shape;
  shape.__set_circle(circle);
  body.__set_shapes({shape});
  const auto color = static_cast<::shared::Color::type>(1);
  body.__set_color(color);
  body.__set_diameter(2.0 * radius);
  body.__set_shapeType(::scene::ShapeType::BALL);
  body.bodyType =
      dynamic ? ::scene::BodyType::DYNAMIC : ::scene::BodyType::STATIC;
  return body;
}

::scene::Body buildPolygon(float x, float y,
                           const std::vector<::scene::Vector>& vertices,
                           float angle, bool dynamic) {
  ::scene::Body body;
  body.__set_position(getVector(x, y));
  body.__set_angle(angle);
  ::scene::Polygon poly;
  poly.vertices = vertices;
  ::scene::Shape shape;
  shape.__set_polygon(poly);
  body.__set_shapes({shape});
  const auto color = static_cast<::shared::Color::type>(1);
  body.__set_color(color);
  body.__set_shapeType(::scene::ShapeType::UNDEFINED);
  body.bodyType =
      dynamic ? ::scene::BodyType::DYNAMIC : ::scene::BodyType::STATIC;
  return body;
}
