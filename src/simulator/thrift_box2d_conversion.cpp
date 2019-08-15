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
// Conversion from scene::Scene to b2World and back.
//
// Note, two types of units are used in this module: pixels and meters.
// Pixels refer to units in scene::Scene, meters refer to units in b2World.
// They could be converted to each other with m2p and p2m functions.

#include <memory>
#include <stdexcept>
#include <vector>

#include "thrift_box2d_conversion.h"

namespace {

constexpr float DEFAULT_GRAVITY = -9.8;
constexpr float DEFAULT_DENSITY = 0.25;
// Friction is used to make objects slide along each other realistically. Box2D
// supports static and dynamic friction, but uses the same parameter for both.
// The friction parameter is usually set between 0 and 1, but can be any
// non-negative value. A friction value of 0 turns off friction and a value of
// 1 makes the friction strong.
constexpr float DEFAULT_FRICTION = 0.5;
// How bouncy the objects are from 0 to 1.
constexpr float DEFAULT_RESTITUTION = 0.2;
// Damping is used to reduce the world velocity of bodies. Damping is different
// than friction because friction only occurs with contact. Damping is not a
// replacement for friction and the two effects should be used together.
// Damping parameters should be between 0 and infinity, with 0 meaning no
// damping, and infinity meaning full damping. Normally you will use a damping
// value between 0 and 0.1. I generally do not use linear damping because it
// makes bodies look like they are floating.
constexpr float DEFAULT_ANGULAR_DAMPING = 0.01;
constexpr float DEFAULT_LINEAR_DAMPING = 0.0;

float m2p(float meters) { return meters * PIXELS_IN_METER; }

float p2m(float pixels) { return pixels / PIXELS_IN_METER; }

b2FixtureDef getFixtureFromThriftBody(const ::scene::Body& pThriftBody) {
  b2FixtureDef fixture;
  if (pThriftBody.bodyType == ::scene::BodyType::DYNAMIC) {
    // Set the shape density to be non-zero, so it will be dynamic.
    fixture.density = DEFAULT_DENSITY;
  }
  fixture.friction = DEFAULT_FRICTION;
  fixture.restitution = DEFAULT_RESTITUTION;

  return fixture;
}

void addFixturesToBody(b2Body& body, const ::scene::Body& pThriftBody) {
  for (const ::scene::Shape& thriftShape : pThriftBody.shapes) {
    b2FixtureDef fixture = getFixtureFromThriftBody(pThriftBody);
    // Slightly odd Box2d interface requires for polygonShape/circleShape
    // to exist untill CreateFixture is called.
    b2PolygonShape polygonShape;
    b2CircleShape circleShape;
    if (thriftShape.__isset.polygon) {
      std::vector<b2Vec2> vertices;
      vertices.reserve(thriftShape.polygon.vertices.size());
      for (const auto& thriftVertex : thriftShape.polygon.vertices) {
        vertices.emplace_back(p2m(thriftVertex.x), p2m(thriftVertex.y));
      }
      polygonShape.Set(vertices.data(), vertices.size());
      fixture.shape = &polygonShape;
    } else if (thriftShape.__isset.circle) {
      circleShape.m_radius = p2m(thriftShape.circle.radius);
      fixture.shape = &circleShape;
    } else {
      throw std::runtime_error("Unexpected shape");
    }
    body.CreateFixture(&fixture);
  }
}

b2BodyDef convertThriftBodyToBox2dBodyDef(const ::scene::Body& pThriftBody) {
  b2BodyDef bodyDef;
  bodyDef.position.Set(p2m(pThriftBody.position.x),
                       p2m(pThriftBody.position.y));
  bodyDef.angle = pThriftBody.angle;
  bodyDef.angularDamping = DEFAULT_ANGULAR_DAMPING;
  bodyDef.linearDamping = DEFAULT_LINEAR_DAMPING;

  if (pThriftBody.bodyType == ::scene::BodyType::DYNAMIC) {
    bodyDef.type = b2_dynamicBody;
  }
  return bodyDef;
}

void addBodiesToWorld(b2WorldWithData& world,
                      const std::vector<::scene::Body>& pThriftBodies,
                      const Box2dData::ObjectType object_type) {
  for (size_t i = 0; i < pThriftBodies.size(); ++i) {
    const ::scene::Body& thriftBody = pThriftBodies[i];
    // Create bodyDef
    b2BodyDef bodyDef = convertThriftBodyToBox2dBodyDef(thriftBody);
    // Create a body
    b2Body* body = world.CreateBody(&bodyDef);   // not owned
    Box2dData* box2d_data = world.CreateData();  // not owned
    box2d_data->object_id = i;
    box2d_data->object_type = object_type;
    body->SetUserData(box2d_data);

    addFixturesToBody(*body, thriftBody);
  }
}

// Create a body one corner in the given position. Height and width could be
// negative.
::scene::Body buildStaticBox(float x, float y, float width, float height) {
  ::scene::Vector bodyPos;
  bodyPos.x = x + width / 2;
  bodyPos.y = y + height / 2;
  std::vector<::scene::Vector> vertices;
  for (int i = 0; i < 4; i++) {
    ::scene::Vector v;
    v.x = (-0.5 + (i == 2 || i == 3)) * width;
    v.y = (-0.5 + (i == 1 || i == 2)) * height;
    vertices.push_back(v);
  }
  ::scene::Polygon box;
  box.__set_vertices(vertices);
  ::scene::Shape shape;
  shape.__set_polygon(box);
  ::scene::Body body;
  body.__set_shapes({shape});
  body.__set_position(bodyPos);
  return body;
}

}  // namespace

std::unique_ptr<b2WorldWithData> convertSceneToBox2dWorld(
    const ::scene::Scene& scene) {
  const b2Vec2 gravity(0.0f, DEFAULT_GRAVITY);
  std::unique_ptr<b2WorldWithData> world(new b2WorldWithData(gravity));
  addBodiesToWorld(*world, scene.bodies, Box2dData::GENERAL);
  addBodiesToWorld(*world, scene.user_input_bodies, Box2dData::USER);
  return world;
}

std::unique_ptr<b2WorldWithData> convertSceneToBox2dWorld_with_bounding_boxes(
    const ::scene::Scene& scene) {
  std::unique_ptr<b2WorldWithData> world{convertSceneToBox2dWorld(scene)};
  const std::vector<::scene::Body> bounding_boxes{
      buildStaticBox(0, 0, scene.width, -10),
      buildStaticBox(0, scene.height, scene.width, 10),
      buildStaticBox(0, 0, -10, scene.height),
      buildStaticBox(scene.width, 0, 10, scene.height)};
  addBodiesToWorld(*world, bounding_boxes, Box2dData::BOUNDING_BOX);
  return world;
}

::scene::Scene updateSceneFromWorld(const ::scene::Scene& scene,
                                    const b2WorldWithData& world) {
  ::scene::Scene new_scene = scene;
  const b2Body* box2dBody = world.GetBodyList();
  for (; box2dBody != nullptr; box2dBody = box2dBody->GetNext()) {
    if (box2dBody->GetUserData() == nullptr) {
      throw std::runtime_error("Found a Box2d body without userdata");
    }
    const Box2dData* box2d_data =
        static_cast<Box2dData*>(box2dBody->GetUserData());
    if (box2d_data == nullptr) {
      throw std::runtime_error(
          "Found a Box2d body with userdata that is not Box2dData");
    }
    if (box2d_data->object_type == Box2dData::BOUNDING_BOX) {
      // Bounding boxes do not present in the scene.
      continue;
    }
    auto& object_list = (box2d_data->object_type == Box2dData::GENERAL)
                            ? new_scene.bodies
                            : new_scene.user_input_bodies;
    ::scene::Body& body = object_list.at(box2d_data->object_id);
    body.position.__set_x(m2p(box2dBody->GetPosition().x));
    body.position.__set_y(m2p(box2dBody->GetPosition().y));
    body.__set_angle(box2dBody->GetAngle());
  }
  return new_scene;
}

::scene::Shape p2mShape(const ::scene::Shape& shape) {
  ::scene::Shape scaledShape;
  std::vector<::scene::Vector> vertices;
  vertices.reserve(shape.polygon.vertices.size());
  for (const auto& v : shape.polygon.vertices) {
    ::scene::Vector vec;
    vec.__set_x(p2m(v.x));
    vec.__set_y(p2m(v.y));
    vertices.emplace_back(vec);
  }
  ::scene::Polygon poly;
  poly.__set_vertices(vertices);
  scaledShape.__set_polygon(poly);
  return scaledShape;
}
