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

#include "logger.h"
#include "thrift_box2d_conversion.h"

#include "gen-cpp/scene_types.h"
#include "gen-cpp/task_types.h"

namespace {
constexpr double BODY_POS_X = 1.0, BODY_POS_Y = 1.0;
constexpr double ANGLE = 3.14;
constexpr int NUM_POLY_VERTICES = 4;
constexpr double V_X[NUM_POLY_VERTICES] = {-1.0, -1.0, 1.0, 1.0};
constexpr double V_Y[NUM_POLY_VERTICES] = {-1.0, 1.0, 1.0, -1.0};
constexpr double GRAVITY_X = 0, GRAVITY_Y = -9.8;
constexpr int WORLD_WIDTH = 512, WORLD_HEIGHT = 512;
constexpr scene::BodyType::type BODY_TYPE = scene::BodyType::type::DYNAMIC;
constexpr int NUM_BODIES = 1;
}  // namespace

class BackendTest : public ::testing::Test {
 protected:
  void SetUp() override { scene_ = create_scene(); }

  static scene::Scene create_scene() {
    scene::Body body;
    scene::Vector bodyPos;
    bodyPos.__set_x(BODY_POS_X);
    bodyPos.__set_y(BODY_POS_Y);
    body.__set_position(bodyPos);
    body.__set_angle(ANGLE);
    scene::Polygon poly;
    std::vector<scene::Vector> vertices;
    for (int i = 0; i < 4; i++) {
      scene::Vector v;
      v.x = V_X[i];
      v.y = V_Y[i];
      vertices.push_back(v);
    }
    poly.__set_vertices(vertices);
    scene::Shape shape;
    shape.__set_polygon(poly);
    body.__set_shapes({shape});
    body.bodyType = scene::BodyType::DYNAMIC;
    std::vector<scene::Body> bodies;
    bodies.push_back(body);

    // Put an input box at (100, 100).
    std::vector<scene::IntVector> inputPoints;
    for (int dx = 0; dx < 10; ++dx) {
      for (int dy = 0; dy < 10; ++dy) {
        scene::IntVector v;
        v.x = 100 + dx;
        v.y = 100 + dy;
        inputPoints.push_back(v);
      }
    }
    std::vector<scene::Body> user_input_bodies = mergeUserInputIntoScene(
        inputPoints, bodies, /*keep_space_around_bodies=*/true,
        /*allow_occlusions=*/false, WORLD_HEIGHT, WORLD_WIDTH);

    scene::Scene scene;
    scene.__set_bodies(bodies);
    scene.__set_user_input_bodies(user_input_bodies);
    scene.__set_width(WORLD_WIDTH);
    scene.__set_height(WORLD_HEIGHT);
    return scene;
  }

  ::scene::Scene scene_;
};

TEST_F(BackendTest, DISABLED_ThriftToBox2dConversion) {
  std::unique_ptr<b2WorldWithData> box2dWorld =
      convertSceneToBox2dWorld(scene_);

  // As thrift uses double and box2d uses float, so can't use == to compare
  EXPECT_FLOAT_EQ(box2dWorld->GetGravity().x, GRAVITY_X);
  EXPECT_FLOAT_EQ(box2dWorld->GetGravity().y, GRAVITY_Y);

  const b2Body* body = box2dWorld->GetBodyList();
  ASSERT_NE(body, nullptr) << "world.bodyList is None";

  unsigned int sceneBodyCount = 0;
  unsigned int userBodyCount = 0;
  while (body != nullptr) {
    Box2dData* box2d_data = (Box2dData*)body->GetUserData();
    if (box2d_data->object_type == Box2dData::USER) {
      body = body->GetNext();
      userBodyCount++;
      continue;
    }

    sceneBodyCount++;
    EXPECT_FLOAT_EQ(body->GetPosition().x * PIXELS_IN_METER, BODY_POS_X);
    EXPECT_FLOAT_EQ(body->GetPosition().y * PIXELS_IN_METER, BODY_POS_Y);

    EXPECT_FLOAT_EQ(body->GetAngle(), ANGLE);

    const b2Fixture* fixture = body->GetFixtureList();
    ASSERT_NE(fixture, nullptr) << "body->FixtureList is None";

    int fixtureCount = 0;
    while (fixture != nullptr) {
      fixtureCount++;
      const b2Shape* shape = fixture->GetShape();
      ASSERT_NE(shape, nullptr) << "fixture->shape is None";

      ASSERT_EQ(shape->GetType(), b2Shape::Type::e_polygon);
      fixture = fixture->GetNext();
    }
    ASSERT_EQ(fixtureCount, 1);
    body = body->GetNext();
  }
  ASSERT_EQ(sceneBodyCount, 1);
  ASSERT_EQ(userBodyCount, 1);
}

TEST_F(BackendTest, SceneToBox2DAndBackConversion) {
  auto box2dWorld = convertSceneToBox2dWorld(scene_);
  const scene::Scene scene = updateSceneFromWorld(scene_, *box2dWorld);
  EXPECT_FLOAT_EQ(scene.width, WORLD_WIDTH);
  EXPECT_FLOAT_EQ(scene.height, WORLD_HEIGHT);
  const std::vector<scene::Body> bodies = scene.bodies;
  ASSERT_EQ(bodies.size(), NUM_BODIES);
  scene::Body body = bodies[0];
  EXPECT_FLOAT_EQ(body.angle, ANGLE);
  EXPECT_EQ(body.bodyType, BODY_TYPE);
  const scene::Vector bodyPos = body.position;
  EXPECT_FLOAT_EQ(bodyPos.x, BODY_POS_X);
  EXPECT_FLOAT_EQ(bodyPos.y, BODY_POS_Y);
  ASSERT_EQ(body.shapes.size(), 1);
  ASSERT_TRUE(body.shapes[0].__isset.polygon);
  const scene::Polygon poly = body.shapes[0].polygon;
  const std::vector<scene::Vector> vertices = poly.vertices;
  ASSERT_EQ(vertices.size(), NUM_POLY_VERTICES);
  int i = 0;
  for (size_t i = 0; i < vertices.size(); ++i) {
    EXPECT_FLOAT_EQ(vertices[i].x, V_X[i])
        << "Position mismatch for vertex " << i;
    EXPECT_FLOAT_EQ(vertices[i].y, V_Y[i])
        << "Position mismatch for vertex " << i;
  }
}

TEST_F(BackendTest, SceneSimulationDoesntDie) {
  std::unique_ptr<b2WorldWithData> world = convertSceneToBox2dWorld(scene_);
  float32 timeStep = 1.0f / 60.0f;
  int32 velocityIterations = 10;
  int32 positionIterations = 10;

  const std::vector<float> expectedY = {1.0f, 0.98366672, 0.95099998,
                                        0.90199995, 0.83666664};
  // Simulation loop.
  Logger::INFO() << "SceneSimulationDoesntDie: Simulating world";
  for (int32 i = 0; i < 5; i++) {
    Logger::DEBUG() << "Iteration: " << i << "\n";
    b2Body* body = world->GetBodyList();
    unsigned int sceneBodyCount = 0;
    while (body != nullptr) {
      Box2dData* box2d_data = (Box2dData*)body->GetUserData();
      if (box2d_data->object_type == Box2dData::USER) {
        body = body->GetNext();
        continue;
      }
      Logger::DEBUG() << "\tBody: " << sceneBodyCount++ << "\n";
      Logger::DEBUG() << "\t\tX: " << body->GetPosition().x
                      << " Y: " << body->GetPosition().y
                      << " Angle: " << body->GetAngle() << "\n";

      EXPECT_FLOAT_EQ(body->GetPosition().y * PIXELS_IN_METER, expectedY[i]);
      body = body->GetNext();
    }
    // Instruct the world to perform a single step of simulation.
    // It is generally best to keep the time step and iterations fixed.
    world->Step(timeStep, velocityIterations, positionIterations);
  }
}
