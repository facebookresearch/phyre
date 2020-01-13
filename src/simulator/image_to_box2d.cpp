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
#include <math.h>
#include <algorithm>
#include <cmath>
#include <vector>

#include <b2Polygon.h>
#include <clip2tri.h>  //delaunay algo to triangulate polygon(works with holes)
#include <clipper.hpp>

#include "creator.h"
#include "geometry.h"
#include "image_to_box2d.h"
#include "logger.h"
#include "task_utils.h"

#include "gen-cpp/scene_types.h"
#include "gen-cpp/shared_constants.h"

using scene::Body;
using scene::IntVector;
using std::vector;

namespace {

// Simple wrapper over the output buffer.
template <class T>
struct Array2d {
  T* data;
  const int width, height;
};

// ##################
// Actual code
// ##################

// Get absolute polygon vertices from relative polygon values
template <class T>
vector<T> getAbsolutePolygon(const std::vector<T>& relativeVerticies,
                             const T& position, const double angle) {
  std::vector<::scene::Vector> vertices;
  vertices.reserve(relativeVerticies.size());

  for (const ::scene::Vector& p : relativeVerticies) {
    vertices.push_back(geometry::translatePoint(p, position, angle));
  }
  return vertices;
}

template <class Vector, class T>
void fillConvexPoly(const std::vector<Vector>& v, const T color,
                    Array2d<T>* array) {
  struct Edge {
    Vector start, end;
  };

  std::vector<Edge> leftEdges, rightEdges;
  for (size_t i = 0; i < v.size(); ++i) {
    size_t prev = i == 0 ? v.size() - 1 : i - 1;
    if (std::abs(v[i].y - v[prev].y) < 1e-3) {
      continue;
    }
    if (v[prev].y < v[i].y) {
      Edge edge{v[prev], v[i]};
      rightEdges.push_back(edge);
    } else {
      Edge edge{v[i], v[prev]};
      leftEdges.push_back(edge);
    }
  }

  const auto width = array->width;
  const auto height = array->height;
  if (leftEdges.empty() || rightEdges.empty()) return;

  std::sort(leftEdges.begin(), leftEdges.end(),
            [](const Edge& lhs, const Edge& rhs) {
              return lhs.start.y < rhs.start.y;
            });
  std::sort(rightEdges.begin(), rightEdges.end(),
            [](const Edge& lhs, const Edge& rhs) {
              return lhs.start.y < rhs.start.y;
            });
  int leftActive = 0, rightActive = 0;

  auto cmpY = [](const Vector& lhs, const Vector& rhs) {
    return lhs.y < rhs.y;
  };

  const float polygonMinY = std::min_element(v.begin(), v.end(), cmpY)->y;
  const float polygonMaxY = std::max_element(v.begin(), v.end(), cmpY)->y;
  const int drawStartY = std::max<int>(0, std::lrint(polygonMinY));
  const int drawEndY = std::min<int>(height, std::lrint(polygonMaxY));

  auto getX = [](const Edge& edge, float y) {
    const float alpha = (y - edge.start.y) / (edge.end.y - edge.start.y);
    return alpha * (edge.end.x - edge.start.x) + edge.start.x;
  };

  for (int y = drawStartY; y < drawEndY; ++y) {
    while (leftActive + 1 < leftEdges.size() &&
           leftEdges[leftActive].end.y < y + 0.5)
      ++leftActive;
    while (rightActive + 1 < rightEdges.size() &&
           rightEdges[rightActive].end.y < y + 0.5)
      ++rightActive;
    const float leftX = getX(leftEdges[leftActive], y + 0.5);
    const float rightX = getX(rightEdges[rightActive], y + 0.5);
    const int leftXInt = std::max<int>(0, std::lrint(leftX));
    const int rightXInt = std::min<int>(width, std::lrint(rightX));
    if (leftXInt < rightXInt) {
      auto start = array->data + y * width;
      std::fill(&start[leftXInt], &start[rightXInt], color);
    }
  }
}

template <class T>
inline void recomputeLeftRight(const float radius_squared, const int y,
                               const float center_x, const float center_y,
                               const uint8_t color, int* left, int* right,
                               Array2d<T>* array) {
  auto sq = [](float x) { return x * x; };

  const float residual = radius_squared - sq(y - center_y);
  while (sq(*left - center_x) <= residual) *left -= 1;
  while (sq(*right - center_x) <= residual) *right += 1;

  const int left_int = std::max<int>(0, *left + 1);
  const int right_int = std::min<int>(array->width - 1, *right - 1);

  if (left_int <= right_int && 0 <= y && y < array->height) {
    std::fill_n(array->data + y * array->width + left_int,
                right_int - left_int + 1, color);
  }
}

template <class T>
void draw_circle(float center_x, float center_y, float radius, uint8_t color,
                 Array2d<T>* array) {
  center_x -= 0.5;
  center_y -= 0.5;
  const float radius_squared = radius * radius;
  {
    int left = center_x, right = center_x;
    for (int y = center_y + radius + 1; y >= center_y; --y) {
      recomputeLeftRight(radius_squared, y, center_x, center_y, color, &left,
                         &right, array);
    }
  }
  {
    int left = center_x, right = center_x;
    for (int y = center_y - radius; y < center_y; ++y) {
      recomputeLeftRight(radius_squared, y, center_x, center_y, color, &left,
                         &right, array);
    }
  }
}

std::vector<IntVector> filterPointsOutsideCanvass(
    const std::vector<IntVector>& pPointList, const int height,
    const int width) {
  std::vector<IntVector> goodPoints;
  for (const auto& p : pPointList) {
    if (p.x >= 0 && p.x < width && p.y >= 0 && p.y < height) {
      goodPoints.push_back(p);
    }
  }
  return goodPoints;
}
// Renders user bodies into an Image.
template <class T>
void renderSceneBodies(const std::vector<Body>& bodies, int height, int width,
                       T* data) {
  std::fill_n(data, width * height, 0);
  Array2d<T> array = {data, width, height};

  for (const Body& body : bodies) {
    if (body.color == 0) {
      continue;
    }
    const T color = body.color;
    for (const ::scene::Shape& shape : body.shapes) {
      if (shape.__isset.polygon == true) {
        const auto vertices = getAbsolutePolygon(shape.polygon.vertices,
                                                 body.position, body.angle);
        fillConvexPoly(vertices, color, &array);
      } else if (shape.__isset.circle == true) {
        draw_circle(body.position.x, body.position.y, shape.circle.radius,
                    color, &array);
      } else {
        // Siliently ignore.
      }
    }
  }
}

bool doesBallOccludeBody(const ::scene::CircleWithPosition& ball,
                         const Body& body) {
  for (const auto& shape : body.shapes) {
    if (shape.__isset.polygon == true) {
      const auto relativeCenter = geometry::reverseTranslatePoint(
          ball.position, body.position, body.angle);
      if (geometry::doesBallOccludePolygon(shape.polygon.vertices,
                                           relativeCenter, ball.radius)) {
        return true;
      }
    } else if (shape.__isset.circle == true) {
      if (geometry::isPointInsideCircle(ball.position, body.position,
                                        ball.radius + shape.circle.radius)) {
        return true;
      }
    }
  }
  return false;
}

template <class Point>
ClipperLib::Paths polygonToPaths(const vector<Point>& polygon) {
  ClipperLib::Paths paths(1);
  for (const auto& p : polygon) {
    paths[0].push_back(ClipperLib::IntPoint(p.x, p.y));
  }
  return paths;
}

bool doesPolygonOccludeBody(const ::scene::AbsoluteConvexPolygon& polygon,
                            const Body& body) {
  const auto polygon_as_paths = polygonToPaths(polygon.vertices);

  for (const auto& shape : body.shapes) {
    if (shape.__isset.polygon == true) {
      const auto body_polygon =
          getAbsolutePolygon(shape.polygon.vertices, body.position, body.angle);
      ClipperLib::Clipper c;
      c.AddPaths(polygon_as_paths, ClipperLib::ptSubject, true);
      c.AddPaths(polygonToPaths(body_polygon), ClipperLib::ptClip, true);

      ClipperLib::Paths solution;
      c.Execute(ClipperLib::ctIntersection, solution, ClipperLib::pftNonZero,
                ClipperLib::pftNonZero);

      if (solution.size() != 0) {
        return true;
      }
    } else if (shape.__isset.circle == true) {
      if (geometry::doesBallOccludePolygon(polygon.vertices, body.position,
                                           shape.circle.radius)) {
        return true;
      }
    }
  }
  return false;
}

}  // namespace

::scene::Image render(const std::vector<Body>& sceneBodies, const int height,
                      const int width) {
  ::scene::Image result;
  result.__set_height(height);
  result.__set_width(width);
  std::vector<int> values(width * height);
  renderSceneBodies(sceneBodies, height, width, &values[0]);
  result.__set_values(values);
  return result;
}

::scene::Image render(const ::scene::Scene& scene) {
  std::vector<Body> bodies = scene.bodies;
  bodies.insert(bodies.end(), scene.user_input_bodies.begin(),
                scene.user_input_bodies.end());
  return render(bodies, scene.height, scene.width);
}

void renderTo(const ::scene::Scene& scene, uint8_t* buffer) {
  std::vector<Body> bodies = scene.bodies;
  bodies.insert(bodies.end(), scene.user_input_bodies.begin(),
                scene.user_input_bodies.end());
  renderSceneBodies(bodies, scene.height, scene.width, buffer);
}

bool isPointInsideBody(const ::scene::Vector& pPoint, const Body& pBody) {
  const ::scene::Vector relativePoint =
      geometry::reverseTranslatePoint(pPoint, pBody.position, pBody.angle);
  for (const auto& shape : pBody.shapes) {
    if (shape.__isset.polygon == true) {
      if (geometry::isInsidePolygon(shape.polygon.vertices, relativePoint)) {
        return true;
      }
    } else if (shape.__isset.circle == true &&
               geometry::isPointInsideCircle(pPoint, pBody.position,
                                             shape.circle.radius)) {
      return true;
    }
  }
  return false;
}

::scene::Body absolutePolygonToBody(
    const ::scene::AbsoluteConvexPolygon& polygon) {
  float center_x = 0, center_y = 0;
  for (const auto& v : polygon.vertices) {
    center_x += v.x;
    center_y += v.y;
  }
  center_x /= polygon.vertices.size();
  center_y /= polygon.vertices.size();
  std::vector<::scene::Vector> normalized_verticies;
  for (const auto& v : polygon.vertices) {
    normalized_verticies.push_back(getVector(v.x - center_x, v.y - center_y));
  }
  return buildPolygon(center_x, center_y, normalized_verticies);
}

bool mergeUserInputIntoScene(const ::scene::UserInput& userInput,
                             const std::vector<Body>& sceneBodies,
                             bool keepSpaceAroundBodies, bool allowOcclusions,
                             int height, int width, std::vector<Body>* bodies) {
  bool good = true;
  // 1. Adding balls.
  for (const ::scene::CircleWithPosition& ball : userInput.balls) {
    bool hasOcclusions = false;
    for (const Body& sceneBody : sceneBodies) {
      if (doesBallOccludeBody(ball, sceneBody)) {
        hasOcclusions = true;
        good = false;
        break;
      }
    }
    if (!hasOcclusions || allowOcclusions) {
      bodies->push_back(
          buildCircle(ball.position.x, ball.position.y, ball.radius));
    }
  }

  // 2. Adding polygons.
  const auto num_balls = bodies->size();
  for (const ::scene::AbsoluteConvexPolygon& polygon : userInput.polygons) {
    if (!geometry::isConvexPositivePolygon(polygon.vertices)) {
      good = false;
      continue;
    }
    // Need to check both scene bodies and just added balls.
    bool hasOcclusions = false;
    for (int i = 0; i < sceneBodies.size() + num_balls; ++i) {
      const Body& sceneBody = (i < sceneBodies.size())
                                  ? sceneBodies[i]
                                  : (*bodies)[i - sceneBodies.size()];
      if (doesPolygonOccludeBody(polygon, sceneBody)) {
        hasOcclusions = true;
        good = false;
        break;
      }
    }
    if (!hasOcclusions || allowOcclusions) {
      bodies->push_back(absolutePolygonToBody(polygon));
    }
  }

  // 3. Vectorizing and adding points.
  if (userInput.flattened_point_list.empty()) {
    return good;
  }
  if (userInput.flattened_point_list.size() % 2 != 0) {
    throw std::runtime_error(
        "Number of elements in flattened_point_list must be even.");
  }
  std::vector<IntVector> input_points(userInput.flattened_point_list.size() /
                                      2);
  for (int i = 0; i < input_points.size(); ++i) {
    input_points[i].x = userInput.flattened_point_list[2 * i];
    input_points[i].y = userInput.flattened_point_list[2 * i + 1];
  }
  const std::vector<IntVector> goodInputPoints =
      filterPointsOutsideCanvass(input_points, height, width);
  good = good && (goodInputPoints.size() == input_points.size());

  // TODO: re-implement free draw input without opencv.
  return good;
}

vector<IntVector> cleanUpPoints(const vector<IntVector>& input_points,
                                const vector<Body>& sceneBodies,
                                const unsigned height, const unsigned width) {
  // TODO: re-implement without opencv.
  vector<IntVector> points;
  return points;
}

void featurizeScene(const ::scene::Scene& scene, float* buffer) {
  int writeIndex = 0;
  std::vector<Body> bodies = scene.bodies;
  bodies.insert(bodies.end(), scene.user_input_bodies.begin(),
                scene.user_input_bodies.end());
  for (const Body& body : bodies) {
    if (body.shapeType != ::scene::ShapeType::UNDEFINED) {
      featurizeBody(body, scene.height, scene.width, buffer + writeIndex);
      writeIndex += kObjectFeatureSize;
    }
  }
}

// Convert angle in (-float-min, float-max) to be in [0,2pi)
float wrapAngleRadians(float angle) {
  angle = fmod(angle, 2.0 * M_PI);
  if (angle < 0.0) {
    angle += 2.0 * M_PI;
  }
  return angle;
}

void featurizeBody(const Body& body, int sceneHeight, int sceneWidth,
                   float* buffer) {
  static_assert(kObjectFeatureSize == 14);
  *buffer++ = static_cast<float>(body.position.x) / sceneWidth;
  *buffer++ = static_cast<float>(body.position.y) / sceneHeight;
  *buffer++ = wrapAngleRadians(body.angle) / (2. * M_PI);
  *buffer++ = static_cast<float>(body.diameter) / sceneWidth;
  // One hot encode the shapeTyoe and color
  for (int i = 0; i < kNumShapes; ++i) {
    *buffer++ = static_cast<float>(i == body.shapeType - 1);
  }
  for (int i = 0; i < kNumColors; ++i) {
    *buffer++ = static_cast<float>(i == body.color - 1);
  }
}
