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
#include <cmath>
#include <vector>

namespace geometry {

constexpr float kZeroLengthEdgeEps = 1e-4;
constexpr float kInsidenessEps = 1e-5;

// point <- rotate(point, angle).
template <class Point>
Point rotatePoint(const Point& point, float angle) {
  Point output;
  const auto cosAngle = std::cos(angle);
  const auto sinAngle = std::sin(angle);
  output.x = point.x * cosAngle - point.y * sinAngle;
  output.y = point.x * sinAngle + point.y * cosAngle;
  return output;
}

// point <- point + shift.
template <class Point>
Point translatePoint(const Point& point, const Point& shift) {
  Point output;
  output.x = point.x + shift.x;
  output.y = point.y + shift.y;
  return output;
}

// point <- rotate(point, angle) + shift.
template <class Point>
Point translatePoint(const Point& point, const Point& shift, float angle) {
  return translatePoint(rotatePoint(point, angle), shift);
}

// point <- point - shift.
template <class Point>
Point reverseTranslatePoint(const Point& point, const Point& shift) {
  Point output;
  output.x = point.x - shift.x;
  output.y = point.y - shift.y;
  return output;
}

// point <- rotate(point - shift, -angle).
template <class Point>
Point reverseTranslatePoint(const Point& point, const Point& shift,
                            float angle) {
  return rotatePoint(reverseTranslatePoint(point, shift), -angle);
}
template <class Point>
float innerProduct(const Point& p1, const Point& p2) {
  return p1.x * p2.x + p1.y * p2.y;
}

template <class Point>
float vectorProduct(const Point& v1, const Point& v2) {
  return v1.x * v2.y - v1.y * v2.x;
}

template <class Point>
float squareDistance(const Point& point1, const Point& point2) {
  const float dx = point1.x - point2.x;
  const float dy = point1.y - point2.y;
  return dx * dx + dy * dy;
}

template <class Point>
Point vectorTo(const Point& start, const Point& end) {
  Point vector;
  vector.x = end.x - start.x;
  vector.y = end.y - start.y;
  return vector;
}

template <class Point>
bool isConvexPositivePolygon(const std::vector<Point>& points) {
  for (int i = 0; i < points.size(); ++i) {
    const auto& p1 = points[i];
    const auto& p2 = points[(i + 1) % points.size()];
    const auto& p3 = points[(i + 2) % points.size()];
    if (vectorProduct(vectorTo(p1, p2), vectorTo(p2, p3)) <= 0) {
      return false;
    }
  }
  return true;
}

template <class Point>
float squareDistanceToSegment(const Point& left, const Point& right,
                              const Point& point) {
  const Point leftRight = vectorTo(left, right);
  const float projectionLength = innerProduct(leftRight, vectorTo(left, point));
  const float squareEdgeLength = squareDistance(left, right);
  if (projectionLength < 0 || squareEdgeLength < kZeroLengthEdgeEps) {
    return squareDistance(left, point);
  } else if (projectionLength > squareDistance(left, right)) {
    return squareDistance(right, point);
  } else {
    const float num = (leftRight.y * point.x - leftRight.x * point.y +
                       right.x * left.y - right.y * left.x);
    return num * num / squareEdgeLength;
  }
}

template <class Point>
float squareDistanceToPolygon(const std::vector<Point>& polygon,
                              const Point& point) {
  auto bestDistance =
      squareDistanceToSegment(polygon[polygon.size() - 1], polygon[0], point);
  for (size_t i = 0; i + 1 < polygon.size(); ++i) {
    bestDistance =
        std::min(bestDistance,
                 squareDistanceToSegment(polygon[i], polygon[i + 1], point));
  }
  return bestDistance;
}

// Strictly inside.
template <class Point>
bool isInsidePolygon(const std::vector<Point>& polygon, const Point& point) {
  for (size_t i = 0; i < polygon.size(); ++i) {
    size_t j = (i == 0) ? polygon.size() - 1 : i - 1;
    if (vectorProduct(vectorTo(polygon[j], polygon[i]),
                      vectorTo(polygon[j], point)) <= 0) {
      return false;
    }
  }
  return true;
}

// Non-zero intersection. Touching is ok.
template <class Point>
bool doesBallOccludePolygon(const std::vector<Point>& polygon,
                            const Point& center, const float radius) {
  if (isInsidePolygon(polygon, center)) {
    return true;
  }
  const float squareDistance = squareDistanceToPolygon(polygon, center);
  if (std::sqrt(squareDistance) + kInsidenessEps < radius) {
    return true;
  }
  return false;
}

// Non-zero intersection. Touching is ok.
template <class Point>
bool isPointInsideCircle(const Point& point, const Point& center,
                         const float radius) {
  return std::sqrt(squareDistance(point, center)) + kInsidenessEps < radius;
}

}  // namespace geometry
