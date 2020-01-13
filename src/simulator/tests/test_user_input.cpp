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
#include <gtest/gtest.h>
#include <math.h>

#include "creator.h"
#include "gen-cpp/scene_types.h"
#include "gen-cpp/shared_constants.h"
#include "gen-cpp/task_types.h"
#include "image_to_box2d.h"
#include "task_io.h"
#include "task_utils.h"

const std::string kTestTaskFolder = "src/simulator/tests/test_data/user_input";

// Check whether any four corners inside the body.
bool isIntPointInsideBody(const ::scene::IntVector& point,
                          const ::scene::Body& body) {
  for (int dx : {0, 1}) {
    for (int dy : {0, 1}) {
      const auto cornerPoint = getVector(point.x + dx, point.y + dy);
      if (isPointInsideBody(cornerPoint, body)) {
        return true;
      }
    }
  }
  return false;
}

void printImage(const ::scene::Image& image) {
  std::vector<std::vector<int>> pixels(image.height);
  int idx = 0;
  for (int y = 0; y < image.height; ++y) {
    for (int x = 0; x < image.width; ++x) {
      pixels[y].push_back(image.values[idx++]);
    }
  }
  for (int y = image.height; y-- > 0;) {
    for (int x = 0; x < image.width; ++x) {
      std::cout << pixels[y][x];
    }
    std::cout << "\n";
  }
}

TEST(UserInputTest, SegfaultUserInput) {
  const auto userInput =
      readInputPointsFromFile(kTestTaskFolder + "/buggy_input_task45.txt");
  ::task::Task task = getTaskFromPath(kTestTaskFolder + "/task00045:000.bin");
  auto bodies = mergeUserInputIntoScene(userInput, task.scene.bodies,
                                        /*keep_space_around_bodies=*/true,
                                        /*allow_occlusions=*/false,
                                        task.scene.width, task.scene.height);
  task.scene.__set_user_input_bodies(bodies);
  simulateTask(task, 1000);
}

TEST(RenderTest, SimpleBoxRendering) {
  // Here is the expected image (dots = 0):
  //  ......
  //  ......
  //  ......
  //  .11...
  //  .11...
  //  .11...
  //  ......

  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  const int height = 7;
  const int width = 6;
  auto img = render(bodies, height, width);
  ASSERT_EQ(img.height, height);
  ASSERT_EQ(img.width, width);
  //  Note that the beginning of the coordinates is at bottom left corner.
  int idx = 0;
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      const bool inside = (x == 1 || x == 2) && (y == 1 || y == 2 || y == 3);
      EXPECT_EQ(img.values[idx], inside ? 1 : 0)
          << "Mistmatch at position (" << x << ", " << y << ")";
      ++idx;
    }
  }
}

TEST(RenderTest, SimpleBoxRenderingAsUserObjectInScene) {
  // Here is the expected image (dots = 0):
  //  ......
  //  ......
  //  ......
  //  .11...
  //  .11...
  //  .11...
  //  ......
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  scene.__set_bodies(bodies);
  auto img = render(scene);
  ASSERT_EQ(img.height, scene.height);
  ASSERT_EQ(img.width, scene.width);
  //  Note that the beginning of the coordinates is at bottom left corner.
  int idx = 0;
  for (int y = 0; y < scene.height; ++y) {
    for (int x = 0; x < scene.width; ++x) {
      const bool inside = (x == 1 || x == 2) && (y == 1 || y == 2 || y == 3);
      EXPECT_EQ(img.values[idx], inside ? 1 : 0)
          << "Mistmatch at position (" << x << ", " << y << ")";
      ++idx;
    }
  }
}

TEST(RenderTest, SimpleBoxRenderingAsUserObjectInScene_SlightyTilted) {
  // Here is the expected image (dots = 0):
  //  ......
  //  ......
  //  ......
  //  .11...
  //  .11...
  //  .11...
  //  ......
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  for (float angle : {0.1, -0.1, 0.001}) {
    const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3, angle)};
    scene.__set_bodies(bodies);
    auto img = render(scene);
    ASSERT_EQ(img.height, scene.height);
    ASSERT_EQ(img.width, scene.width);
    //  Note that the beginning of the coordinates is at bottom left corner.
    int idx = 0;
    for (int y = 0; y < scene.height; ++y) {
      for (int x = 0; x < scene.width; ++x) {
        const bool inside = (x == 1 || x == 2) && (y == 1 || y == 2 || y == 3);
        ASSERT_EQ(img.values[idx], inside ? 1 : 0)
            << "Mistmatch at position (" << x << ", " << y << ")";
        ++idx;
      }
    }
  }
}

TEST(RenderTest, SimpleBoxNearBoredrRendering) {
  // This test is equivalent to SimpleBoxRendering but the field is smaller and
  // so the box touches the top of the canvas. And so currently the render
  // outputs this:
  //  .11...
  //  .11...
  //  .11...
  //  .11...
  //  ......

  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  const int height = 5;
  const int width = 6;
  auto img = render(bodies, height, width);
  ASSERT_EQ(img.height, height);
  ASSERT_EQ(img.width, width);
  //  Note that the beginning of the coordinates is at bottom left corner.
  int idx = 0;
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      const bool inside = (x == 1 || x == 2) && (y == 1 || y == 2 || y == 3);
      EXPECT_EQ(img.values[idx], inside ? 1 : 0)
          << "Mistmatch at position (" << x << ", " << y << ")";
      ++idx;
    }
  }
}

TEST(RenderTest, CircleRendering) {
  // The center is located in the center of pixel (2, 1).
  const std::vector<::scene::Body> bodies = {buildCircle(2.5, 1.5, 1)};
  const int height = 7;
  const int width = 6;
  auto img = render(bodies, height, width);
  ASSERT_EQ(img.height, height);
  ASSERT_EQ(img.width, width);
  // Note that the beginning of the coordinates is at bottom left corner.
  // Here is the expected image (dots = 0):
  //  ......
  //  ......
  //  ......
  //  ......
  //  ..1...
  //  .111..
  //  ..1...

  int idx = 0;
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      const bool inside = (std::abs(x - 2) + std::abs(y - 1)) <= 1;
      EXPECT_EQ(img.values[idx], inside ? 1 : 0)
          << "Mistmatch at position (" << x << ", " << y << ")";
      ++idx;
    }
  }
}

TEST(RenderTest, CircleRendering_OutOfSceen) {
  const int height = 7;
  const int width = 6;
  const std::vector<::scene::Body> balls = {
      buildCircle(-2.5, 1.5, 1),
      buildCircle(12.5, 11.5, 1),
      buildCircle(2.5, -1.5, 1),
      buildCircle(2.5, 11.5, 1),
  };
  for (const auto& ball : balls) {
    // The center is located in the center of pixel (2, 1).
    const std::vector<::scene::Body> bodies = {ball};
    auto img = render(bodies, height, width);
    ASSERT_EQ(img.height, height);
    ASSERT_EQ(img.width, width);
    int idx = 0;
    for (int y = 0; y < height; ++y) {
      for (int x = 0; x < width; ++x) {
        EXPECT_EQ(img.values[idx], 0)
            << "Mistmatch at position (" << x << ", " << y << ") for " << ball;
        ++idx;
      }
    }
  }
}

TEST(RenderTest, CircleRendering_Huge) {
  const int height = 7;
  const int width = 6;
  const std::vector<::scene::Body> balls = {
      buildCircle(2.5, 1.5, 100),
  };
  for (const auto& ball : balls) {
    // The center is located in the center of pixel (2, 1).
    const std::vector<::scene::Body> bodies = {ball};
    auto img = render(bodies, height, width);
    ASSERT_EQ(img.height, height);
    ASSERT_EQ(img.width, width);
    int idx = 0;
    for (int y = 0; y < height; ++y) {
      for (int x = 0; x < width; ++x) {
        EXPECT_EQ(img.values[idx], 1)
            << "Mistmatch at position (" << x << ", " << y << ") for " << ball;
        ++idx;
      }
    }
  }
}

TEST(CleanUpPointsTest, EmptySceneEmptyInput) {
  const auto cleanPoints = cleanUpPoints({}, {}, 100, 100);
  ASSERT_EQ(cleanPoints.size(), 0);
}

TEST(CleanUpPointsTest, FullSceneBoxAndFullInput) {
  const unsigned width = 10, height = 10;
  std::vector<::scene::IntVector> inputPoints;
  for (unsigned x = 0; x < width; ++x) {
    for (unsigned y = 0; y < height; ++y) {
      inputPoints.push_back(getIntVector(x, y));
    }
  }
  const auto cleanPoints = cleanUpPoints(
      inputPoints, {buildBox(0, 0, width, height)}, width, height);
  ASSERT_EQ(cleanPoints.size(), 0);
}

TEST(CleanUpPointsTest, HorizontalBoxAndFullInput) {
  const unsigned width = 100, height = 100;
  std::vector<::scene::IntVector> inputPoints;
  for (unsigned x = 0; x < width; ++x) {
    for (unsigned y = 0; y < height; ++y) {
      inputPoints.push_back(getIntVector(x, y));
    }
  }
  const auto cleanPoints =
      cleanUpPoints(inputPoints, {buildBox(10, 10, 50, 10)}, width, height);
  // Check that inside points are not among clean.
  for (unsigned x = 10; x < 10 + 50; ++x) {
    for (unsigned y = 10; y < 10 + 10; ++y) {
      const auto cit =
          std::find(cleanPoints.begin(), cleanPoints.end(), getIntVector(x, y));
      ASSERT_EQ(cit, cleanPoints.end());
    }
  }
}

TEST(CleanUpPointsTest, HorizontalBoxFromWallAndFullInput) {
  // The same as above but the box goes into the left wall.
  const unsigned width = 100, height = 100;
  std::vector<::scene::IntVector> inputPoints;
  for (unsigned x = 0; x < width; ++x) {
    for (unsigned y = 0; y < height; ++y) {
      inputPoints.push_back(getIntVector(x, y));
    }
  }
  const auto cleanPoints =
      cleanUpPoints(inputPoints, {buildBox(-10, 10, 50, 10)}, width, height);
  // Check that inside points are not among clean.
  for (unsigned x = 10; x < -10 + 50; ++x) {
    for (unsigned y = 10; y < 10 + 10; ++y) {
      const auto cit =
          std::find(cleanPoints.begin(), cleanPoints.end(), getIntVector(x, y));
      ASSERT_EQ(cit, cleanPoints.end());
    }
  }
}

TEST(CleanUpPointsTest, TiltedSmallBoxAndFullInput) {
  const unsigned width = 3, height = 3;
  std::vector<::scene::IntVector> inputPoints;
  for (unsigned x = 0; x < width; ++x) {
    for (unsigned y = 0; y < height; ++y) {
      inputPoints.push_back(getIntVector(x, y));
    }
  }
  // Slightly tilted box should "eat" 4 pixels. Note that rotation is relative
  // to the bottom left corner.
  const auto body = buildBox(1, 1, 1, 1, /*angle=*/0.5);
  const auto cleanPoints = cleanUpPoints(inputPoints, {body}, width, height);
  // Check that inside points are not among clean.
  for (const auto& point : {getIntVector(0, 1), getIntVector(0, 2),
                            getIntVector(1, 1), getIntVector(1, 2)}) {
    const auto cit = std::find(cleanPoints.begin(), cleanPoints.end(), point);
    ASSERT_EQ(cit, cleanPoints.end()) << "Point " << point << " is inside body "
                                      << body << " but wasn't removed";
  }
}

TEST(CleanUpPointsTest, NegativeTiltedSmallBoxAndFullInput) {
  const unsigned width = 3, height = 3;
  std::vector<::scene::IntVector> inputPoints;
  for (unsigned x = 0; x < width; ++x) {
    for (unsigned y = 0; y < height; ++y) {
      inputPoints.push_back(getIntVector(x, y));
    }
  }
  // Slightly tilted box should "eat" 4 pixels. Note that rotation is relative
  // to the bottom left corner.
  const auto body = buildBox(1, 1, 1, 1, /*angle=*/-0.5);
  const auto cleanPoints = cleanUpPoints(inputPoints, {body}, width, height);
  // Check that inside points are not among clean.
  for (const auto& point : {getIntVector(1, 0), getIntVector(1, 1),
                            getIntVector(2, 0), getIntVector(2, 1)}) {
    const auto cit = std::find(cleanPoints.begin(), cleanPoints.end(), point);
    ASSERT_EQ(cit, cleanPoints.end()) << "Point " << point << " is inside body "
                                      << body << " but wasn't removed";
  }
}

TEST(CleanUpPointsTest, TiltedBoxAndFullInput) {
  const unsigned width = 200, height = 200;
  std::vector<::scene::IntVector> inputPoints;
  for (unsigned x = 0; x < width; ++x) {
    for (unsigned y = 0; y < height; ++y) {
      inputPoints.push_back(getIntVector(x, y));
    }
  }
  // Put box in the middle of the scene so that it cannot reach a wall.
  const auto body = buildBox(100, 100, 50, 10, /*angle=*/1.);
  const auto cleanPoints = cleanUpPoints(inputPoints, {body}, width, height);
  // Check that inside points are not among clean.
  for (const auto& point : inputPoints) {
    if (isIntPointInsideBody(point, body)) {
      const auto cit = std::find(cleanPoints.begin(), cleanPoints.end(), point);
      ASSERT_EQ(cit, cleanPoints.end())
          << "Point " << point << " is inside body " << body
          << " but wasn't removed";
    }
  }
}

TEST(CleanUpPointsTest, CircleAndFullInput) {
  const unsigned width = 200, height = 200;
  std::vector<::scene::IntVector> inputPoints;
  for (unsigned x = 0; x < width; ++x) {
    for (unsigned y = 0; y < height; ++y) {
      inputPoints.push_back(getIntVector(x, y));
    }
  }
  // Put box in the middle of the scene so that it cannot reach a wall.
  const auto body = buildCircle(100, 100, 10);
  const auto cleanPoints = cleanUpPoints(inputPoints, {body}, width, height);
  // Check that inside points are not among clean.
  for (const auto& point : inputPoints) {
    if (isIntPointInsideBody(point, body)) {
      const auto cit = std::find(cleanPoints.begin(), cleanPoints.end(), point);
      ASSERT_EQ(cit, cleanPoints.end())
          << "Point " << point << " is inside body " << body
          << " but wasn't removed";
    }
  }
}

TEST(AddUserInputTest, DISABLED_AddPoints) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  scene.__set_bodies(bodies);

  ::scene::UserInput user_input;
  // Single point (5, 5).
  user_input.flattened_point_list.push_back(5);
  user_input.flattened_point_list.push_back(5);

  std::vector<::scene::Body> user_bodies;
  bool good_input = mergeUserInputIntoScene(
      user_input, bodies,
      /*keep_space_around_bodies=*/false, /*allow_occlusions=*/false,
      scene.height, scene.width, &user_bodies);
  ASSERT_EQ(user_bodies.size(), 1);
  ASSERT_EQ(good_input, true);
}

TEST(AddUserInputTest, AddRectangle) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  scene.__set_bodies(bodies);

  ::scene::AbsoluteConvexPolygon polygon;
  polygon.vertices.push_back(getVector(4, 4));
  polygon.vertices.push_back(getVector(5, 4));
  polygon.vertices.push_back(getVector(5, 5));
  polygon.vertices.push_back(getVector(4, 5));
  ::scene::UserInput user_input;
  user_input.polygons.push_back(polygon);

  std::vector<::scene::Body> user_bodies;
  bool good_input = mergeUserInputIntoScene(
      user_input, bodies,
      /*keep_space_around_bodies=*/true, /*allow_occlusions=*/false,
      scene.height, scene.width, &user_bodies);
  ASSERT_EQ(user_bodies.size(), 1);
  ASSERT_EQ(good_input, true);
}

TEST(AddUserInputTest, AddOccludingRectangle) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  scene.__set_bodies(bodies);

  ::scene::AbsoluteConvexPolygon polygon;
  polygon.vertices.push_back(getVector(2, 3));
  polygon.vertices.push_back(getVector(5, 4));
  polygon.vertices.push_back(getVector(5, 5));
  polygon.vertices.push_back(getVector(4, 5));
  ::scene::UserInput user_input;
  user_input.polygons.push_back(polygon);

  std::vector<::scene::Body> user_bodies;
  bool good_input = mergeUserInputIntoScene(
      user_input, bodies,
      /*keep_space_around_bodies=*/true, /*allow_occlusions=*/false,
      scene.height, scene.width, &user_bodies);
  ASSERT_EQ(user_bodies.size(), 0);
  ASSERT_EQ(good_input, false);
}

TEST(AddUserInputTest, AddBall) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  scene.__set_bodies(bodies);
  const float radius = 1.0;
  ::scene::CircleWithPosition ball;
  ball.position.__set_x(5);
  ball.position.__set_y(5);
  ball.__set_radius(radius);
  ::scene::UserInput user_input;
  user_input.balls.push_back(ball);

  std::vector<::scene::Body> user_bodies;
  bool good_input = mergeUserInputIntoScene(
      user_input, bodies,
      /*keep_space_around_bodies=*/true, /*allow_occlusions=*/false,
      scene.height, scene.width, &user_bodies);
  ASSERT_EQ(user_bodies.size(), 1);
  ASSERT_EQ(user_bodies[0].shapeType, ::scene::ShapeType::BALL);
  ASSERT_EQ(user_bodies[0].diameter, 2.0 * radius);
  ASSERT_EQ(good_input, true);
}

TEST(AddUserInputTest, AddOccludingBall) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildBox(1, 1, 2, 3)};
  scene.__set_bodies(bodies);

  ::scene::CircleWithPosition ball;
  ball.position.__set_x(3);
  ball.position.__set_y(3);
  ball.__set_radius(1);
  ::scene::UserInput user_input;
  user_input.balls.push_back(ball);

  std::vector<::scene::Body> user_bodies;
  bool good_input = mergeUserInputIntoScene(
      user_input, bodies,
      /*keep_space_around_bodies=*/true, /*allow_occlusions=*/false,
      scene.height, scene.width, &user_bodies);
  ASSERT_EQ(user_bodies.size(), 0);
  ASSERT_EQ(good_input, false);
}

TEST(AddUserInputTest, AddOccludingBallForBallScene) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildCircle(2, 3, 1)};
  scene.__set_bodies(bodies);

  // Distance is 2.
  ::scene::CircleWithPosition ball;
  ball.position.__set_x(4);
  ball.position.__set_y(3);
  ball.__set_radius(1.01);
  ::scene::UserInput user_input;
  user_input.balls.push_back(ball);

  std::vector<::scene::Body> user_bodies;
  bool good_input = mergeUserInputIntoScene(
      user_input, bodies,
      /*keep_space_around_bodies=*/true, /*allow_occlusions=*/false,
      scene.height, scene.width, &user_bodies);
  ASSERT_EQ(user_bodies.size(), 0);
  ASSERT_EQ(good_input, false);
}

TEST(AddUserInputTest, AddBallForBallScene) {
  ::scene::Scene scene;
  scene.__set_height(7);
  scene.__set_width(6);
  const std::vector<::scene::Body> bodies = {buildCircle(2, 3, 1)};
  scene.__set_bodies(bodies);

  // Distance is 2.
  const float radius = 0.5;
  ::scene::CircleWithPosition ball;
  ball.position.__set_x(4);
  ball.position.__set_y(3);
  ball.__set_radius(radius);
  ::scene::UserInput user_input;
  user_input.balls.push_back(ball);

  std::vector<::scene::Body> user_bodies;
  bool good_input = mergeUserInputIntoScene(
      user_input, bodies,
      /*keep_space_around_bodies=*/true, /*allow_occlusions=*/false,
      scene.height, scene.width, &user_bodies);
  ASSERT_EQ(user_bodies.size(), 1);
  ASSERT_EQ(user_bodies[0].shapeType, ::scene::ShapeType::BALL);
  ASSERT_EQ(user_bodies[0].diameter, 2.0 * radius);
  ASSERT_EQ(good_input, true);
}

TEST(WrapAngleTest, TestAngles) {
  auto const smallPos = 0.7 * 2. * M_PI;
  auto const medPos = 1.5 * 2. * M_PI;
  auto const largePos = 2.3 * 2. * M_PI;

  auto const smallNeg = -0.4 * 2. * M_PI;
  auto const medNeg = -1.2 * 2. * M_PI;
  auto const largeNeg = -3.7 * 2. * M_PI;

  ASSERT_TRUE(abs(wrapAngleRadians(smallPos) - smallPos) < 1e-6);
  ASSERT_TRUE(abs(wrapAngleRadians(medPos) - (0.5 * 2. * M_PI)) < 1e-6);
  ASSERT_TRUE(abs(wrapAngleRadians(largePos) - (0.3 * 2. * M_PI)) < 1e-6);

  ASSERT_TRUE(abs(wrapAngleRadians(smallNeg) - (0.6 * 2. * M_PI)) < 1e-6);
  ASSERT_TRUE(abs(wrapAngleRadians(medNeg) - (0.8 * 2. * M_PI)) < 1e-6);
  ASSERT_TRUE(abs(wrapAngleRadians(largeNeg) - (0.3 * 2. * M_PI)) < 1e-6);
}
