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

#include <gtest/gtest.h>

#include "geometry.h"

class GeometryTest : public ::testing::Test {
 protected:
  struct Point {
    float x, y;
  };

  void expectPointNear(const Point& p1, const Point& p2) {
    ASSERT_NEAR(p1.x, p2.x, 1e-5);
    ASSERT_NEAR(p1.y, p2.y, 1e-5);
  }
};

TEST_F(GeometryTest, TestTranslatePoint) {
  const Point p1{0, 0};
  const Point p2{3, 0};
  const Point p3{0, 4};
  expectPointNear(geometry::translatePoint(Point{1, 0}, Point{0, 0}, 0),
                  Point{1, 0});
  expectPointNear(geometry::translatePoint(Point{1, 0}, Point{10, 1}, 0),
                  Point{11, 1});
  expectPointNear(geometry::translatePoint(Point{1, 0}, Point{0, 0}, M_PI_2),
                  Point{0, 1});
  expectPointNear(geometry::translatePoint(Point{1, 0}, Point{1, 1}, M_PI_2),
                  Point{1, 2});
}

TEST_F(GeometryTest, TestDistance) {
  const Point p1{0, 0};
  const Point p2{3, 0};
  const Point p3{0, 4};
  EXPECT_FLOAT_EQ(geometry::squareDistance(p1, p2), 3 * 3);
  EXPECT_FLOAT_EQ(geometry::squareDistance(p1, p3), 4 * 4);
  EXPECT_FLOAT_EQ(geometry::squareDistance(p2, p3), 5 * 5);
}

TEST_F(GeometryTest, TestInnerProduct) {
  const Point p1{0, 0};
  const Point p2{3, 0};
  const Point p3{0, 4};
  EXPECT_FLOAT_EQ(geometry::innerProduct(p1, p2), 0);
  EXPECT_FLOAT_EQ(geometry::innerProduct(p1, p3), 0);
  EXPECT_FLOAT_EQ(geometry::innerProduct(p2, p3), 0);

  const Point p12 = geometry::vectorTo(p1, p2);
  const Point p13 = geometry::vectorTo(p1, p3);
  const Point p23 = geometry::vectorTo(p2, p3);
  EXPECT_FLOAT_EQ(geometry::innerProduct(p12, p13), 0);
  EXPECT_FLOAT_EQ(geometry::innerProduct(p12, p23), -9);
}

TEST_F(GeometryTest, TestIsPointInsideCircle) {
  const Point center{1, 0};
  EXPECT_FALSE(
      geometry::isPointInsideCircle(center, Point{0, 0}, /*radius=*/1.0));
  EXPECT_TRUE(
      geometry::isPointInsideCircle(center, Point{0, 0}, /*radius=*/1.1));
  EXPECT_TRUE(
      geometry::isPointInsideCircle(center, Point{1.5, 0}, /*radius=*/1.1));
  EXPECT_FALSE(
      geometry::isPointInsideCircle(center, Point{0, 1.5}, /*radius=*/1));
}

TEST_F(GeometryTest, TestIsPointInsidePolygon) {
  const std::vector<Point> polygon{{0., 0.}, {1., 0.}, {1., 1.}, {0., 1.}};
  EXPECT_TRUE(geometry::isInsidePolygon(polygon, Point{0.5, 0.5}));
  EXPECT_FALSE(geometry::isInsidePolygon(polygon, Point{1.5, 0.5}));
}

TEST_F(GeometryTest, TestSquareDistanceToSegment) {
  const Point left{0, 0};
  const Point right{0, 4};
  // Closest point is on the left.
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{0, 0}),
                  0.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{1, 0}),
                  1.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{-1, 0}),
                  1.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{0, -1}),
                  1.);
  // Closest point is in the middle.
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{0, 3}),
                  0.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{1, 3}),
                  1.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{-1, 3}),
                  1.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToSegment(left, right, Point{-2, 3}),
                  4.);
}

TEST_F(GeometryTest, TestIsConvexPolygon) {
  const std::vector<Point> triangle{Point{0, 0}, Point{100, 0}, Point{0, 1}};
  EXPECT_TRUE(geometry::isConvexPositivePolygon(triangle));
  const std::vector<Point> neagive_triangle{triangle[0], triangle[2],
                                            triangle[1]};
  EXPECT_FALSE(geometry::isConvexPositivePolygon(neagive_triangle));

  const std::vector<Point> convex_polygon{Point{0, 0}, Point{100, 0},
                                          Point{100, 100}, Point{50, 200},
                                          Point{0, 100}};
  EXPECT_TRUE(geometry::isConvexPositivePolygon(convex_polygon));
  const std::vector<Point> non_convex_polygon{Point{0, 0}, Point{100, 0},
                                              Point{100, 100}, Point{50, 20},
                                              Point{0, 100}};
  EXPECT_FALSE(geometry::isConvexPositivePolygon(non_convex_polygon));
}

TEST_F(GeometryTest, TestSquareDistanceToPolygon_Triangle) {
  const std::vector<Point> triangle{Point{0, 0}, Point{100, 0}, Point{0, 1}};
  ASSERT_TRUE(geometry::isConvexPositivePolygon(triangle));
  EXPECT_FLOAT_EQ(geometry::squareDistanceToPolygon(triangle, Point{0, 0}), 0.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToPolygon(triangle, Point{0.1, -0.1}),
                  0.1 * 0.1);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToPolygon(triangle, Point{-4., -5}),
                  4 * 4 + 5 * 5);
}

TEST_F(GeometryTest, TestSquareDistanceToPolygon_TrickyTriangle) {
  const std::vector<Point> triangle{Point{0, 0}, Point{100, 1}, Point{-100, 1}};
  ASSERT_TRUE(geometry::isConvexPositivePolygon(triangle));
  EXPECT_FLOAT_EQ(geometry::squareDistanceToPolygon(triangle, Point{0, 0}), 0.);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToPolygon(triangle, Point{0., 1.0}),
                  0.0);
  EXPECT_FLOAT_EQ(geometry::squareDistanceToPolygon(triangle, Point{0., 2.0}),
                  1.0);
}

TEST_F(GeometryTest, TestSquareDistanceToPolygon_Box) {
  const std::vector<Point> box{Point{1, 1}, Point{3, 1}, Point{3, 4},
                               Point{1, 4}};
  ASSERT_TRUE(geometry::isConvexPositivePolygon(box));
  EXPECT_FLOAT_EQ(geometry::squareDistanceToPolygon(box, Point{3, 3}), 0.);
}

TEST_F(GeometryTest, TestDoesBallOccludePolygon_Box) {
  const std::vector<Point> box{Point{1, 1}, Point{3, 1}, Point{3, 4},
                               Point{1, 4}};
  ASSERT_TRUE(geometry::isConvexPositivePolygon(box));
  EXPECT_TRUE(geometry::doesBallOccludePolygon(box, Point{3, 3}, 0.1));
  EXPECT_TRUE(geometry::doesBallOccludePolygon(box, Point{2, 2}, 0.1));
  EXPECT_TRUE(geometry::doesBallOccludePolygon(box, Point{1, 0}, 2.1));
  EXPECT_FALSE(geometry::doesBallOccludePolygon(box, Point{1, 0}, 0.1));
  EXPECT_FALSE(geometry::doesBallOccludePolygon(box, Point{1, 0}, 1.0));
}
