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
#include "task_validation.h"
#include <math.h>
#include <stdexcept>
#include "Box2D/Box2D.h"
#include "geometry.h"
#include "image_to_box2d.h"
#include "thrift_box2d_conversion.h"

namespace {

// One tenth of a pixel.
constexpr float kBallTouchingThreshold = 0.1 / PIXELS_IN_METER;

const Box2dData* getBodyUserData(const b2Body& body) {
  if (body.GetUserData() == nullptr) {
    throw std::runtime_error("Found a Box2d body without userdata");
  }
  const Box2dData* box2d_data = static_cast<Box2dData*>(body.GetUserData());
  if (box2d_data == nullptr) {
    throw std::runtime_error(
        "Found a Box2d body with userdata that is not Box2dData");
  }
  return box2d_data;
}

size_t getBodyId(const b2Body& body) {
  const Box2dData* box2d_data = getBodyUserData(body);
  return box2d_data->object_id;
}

Box2dData::ObjectType getBodyType(const b2Body& body) {
  const Box2dData* box2d_data = getBodyUserData(body);
  return box2d_data->object_type;
}

b2AABB getAbsoluteAABB(const b2AABB& aabb, const b2Vec2& bodyPos) {
  b2AABB aabb_out;
  aabb_out.lowerBound = geometry::translatePoint(aabb.lowerBound, bodyPos);
  aabb_out.upperBound = geometry::translatePoint(aabb.upperBound, bodyPos);
  return aabb_out;
}

b2AABB getBoundingBoxForBody(const b2Body& body) {
  b2AABB aabb;
  b2Vec2 _pos(0, 0);
  b2Rot _rot(body.GetAngle());
  b2Transform t = b2Transform(_pos, _rot);
  aabb.lowerBound = b2Vec2(FLT_MAX, FLT_MAX);
  aabb.upperBound = b2Vec2(-FLT_MAX, -FLT_MAX);
  for (const b2Fixture* f = body.GetFixtureList(); f; f = f->GetNext()) {
    const b2Shape* shape = f->GetShape();
    const int nChildren = shape->GetChildCount();
    for (int child = 0; child < nChildren; ++child) {
      b2AABB shapeAABB;
      shape->ComputeAABB(&shapeAABB, t, child);
      // box2d uses skin for collision detection so subtract that
      if (shape->GetType() == b2Shape::e_polygon) {
        const b2Vec2 r(shape->m_radius, shape->m_radius);
        shapeAABB.lowerBound = shapeAABB.lowerBound + r;
        shapeAABB.upperBound = shapeAABB.upperBound - r;
      }
      aabb.Combine(shapeAABB);
    }
  }
  return getAbsoluteAABB(aabb, body.GetPosition());
}

::scene::Body createPhantomThriftBody(const b2Body& box2dBody,
                                      const ::scene::Shape& phantomShape) {
  ::scene::Body thriftBody;
  ::scene::Vector bodyPos;
  bodyPos.x = box2dBody.GetPosition().x;
  bodyPos.y = box2dBody.GetPosition().y;
  thriftBody.__set_position(bodyPos);
  thriftBody.__set_angle(box2dBody.GetAngle());
  thriftBody.__set_bodyType(::scene::BodyType::DYNAMIC);

  std::vector<::scene::Shape> thriftShapes;
  thriftShapes.push_back(phantomShape);
  thriftBody.__set_shapes(thriftShapes);
  return thriftBody;
}

::scene::Body getThriftCircleBody(b2Vec2 center, float radius) {
  ::scene::Body thriftBody;
  ::scene::Vector pos;
  pos.__set_x(center.x);
  pos.__set_y(center.y);
  thriftBody.__set_position(pos);
  thriftBody.__set_bodyType(::scene::BodyType::DYNAMIC);

  std::vector<::scene::Shape> thriftShapes;
  ::scene::Circle circle;
  circle.__set_radius(radius);
  ::scene::Shape shape;
  shape.__set_circle(circle);
  thriftShapes.push_back(shape);
  thriftBody.__set_shapes(thriftShapes);
  return thriftBody;
}

float distanceBetween2Points(const ::scene::Vector& pt1,
                             const ::scene::Vector& pt2) {
  return sqrt(pow((pt2.x - pt1.x), 2) + (pow((pt2.y - pt1.y), 2)));
}

float computeDistanceBetweenPointAndLine(const ::scene::Vector& pt,
                                         const ::scene::Vector& pt1,
                                         const ::scene::Vector& pt2) {
  float segment_length = distanceBetween2Points(pt1, pt2);
  if (segment_length == 0) {
    return std::numeric_limits<float>::max();
  }

  return abs((pt2.y - pt1.y) * pt.x - (pt2.x - pt1.x) * pt.y + (pt2.x * pt1.y) -
             (pt2.y * pt1.x)) /
         segment_length;
}

float dotProduct(const ::scene::Vector& vec1, const ::scene::Vector& vec2) {
  return (vec1.x * vec2.x + vec1.y * vec2.y);
}

float dotProduct(const ::scene::Vector& pt, const ::scene::Vector& pt1,
                 const ::scene::Vector& pt2) {
  ::scene::Vector vec1, vec2;
  vec1.x = pt1.x - pt.x;
  vec1.y = pt1.y - pt.y;
  vec2.x = pt2.x - pt.x;
  vec2.y = pt2.y - pt.y;

  return dotProduct(vec1, vec2);
}

// Computes projection distance of first vector(pt->pt1) onto second(pt->pt2)
float vectorProjectionDistance(const ::scene::Vector& pt,
                               const ::scene::Vector& pt1,
                               const ::scene::Vector& pt2) {
  // cos = A.B/(|A|*|B|)
  float denominator =
      distanceBetween2Points(pt1, pt) * distanceBetween2Points(pt2, pt);
  if (denominator == 0) {
    return 0.0f;
  }
  float cosine = dotProduct(pt, pt1, pt2) / denominator;
  return abs(distanceBetween2Points(pt1, pt) * cosine);
}

bool doesLineSegmentIntersectWithCircle(const ::scene::Vector& pt1,
                                        const ::scene::Vector& pt2,
                                        const ::scene::Body& circleBody) {
  ::scene::Vector center = circleBody.position;
  float radius = circleBody.shapes[0].circle.radius;
  // Circle distnace from the line should be in radius range
  if (computeDistanceBetweenPointAndLine(center, pt1, pt2) > radius) {
    return false;
  }

  // Line is in the range but now check with line segment
  float lineDotProductWithCenter = dotProduct(pt1, center, pt2);
  float centerProjectionLength = vectorProjectionDistance(pt1, center, pt2);

  if (lineDotProductWithCenter < 0 && centerProjectionLength > radius) {
    return false;
  }
  float lineSegmentLength = distanceBetween2Points(pt1, pt2);
  if (lineDotProductWithCenter > 0 &&
      centerProjectionLength > (lineSegmentLength + radius)) {
    return false;
  }
  return true;
}

bool isCircleInsideBody(const ::scene::Body& circleBody,
                        const ::scene::Body& baseBody) {
  if (baseBody.__isset.shapes == false) {
    throw std::runtime_error("Expected a shape inside base body");
  }

  if (baseBody.shapes[0].__isset.polygon) {
    ::scene::Polygon poly = baseBody.shapes[0].polygon;

    // if circle's center is outside the polygon then quit
    if (isPointInsideBody(circleBody.position, baseBody) == false) {
      return false;
    }

    size_t nEdges = poly.vertices.size();
    // iterate over all the edges
    for (int i = 0; i < nEdges; i++) {
      ::scene::Vector v1 = geometry::translatePoint(
          poly.vertices[i], baseBody.position, (float)baseBody.angle);
      ::scene::Vector v2 =
          geometry::translatePoint(poly.vertices[(i + 1) % nEdges],
                                   baseBody.position, (float)baseBody.angle);

      if (doesLineSegmentIntersectWithCircle(v1, v2, circleBody)) {
        return false;
      }
    }
    return true;
  }
  return false;
}

bool isAbove(b2AABB aabb1, b2AABB aabb2) {
  return (aabb1.lowerBound.y >= aabb2.upperBound.y);
}

bool isBelow(b2AABB aabb1, b2AABB aabb2) {
  return (aabb1.upperBound.y < aabb2.lowerBound.y);
}

bool isLeftOf(b2AABB aabb1, b2AABB aabb2) {
  return (aabb1.upperBound.x < aabb2.lowerBound.x);
}

bool isRightOf(b2AABB aabb1, b2AABB aabb2) {
  return (aabb1.lowerBound.x > aabb2.upperBound.x);
}

bool checkDirectionalRelationship(
    const b2Body& body1, const b2Body& body2,
    ::task::SpatialRelationship::type relationship) {
  b2AABB aabb1 = getBoundingBoxForBody(body1);
  b2AABB aabb2 = getBoundingBoxForBody(body2);

  switch (relationship) {
    case ::task::SpatialRelationship::ABOVE:
      return isAbove(aabb1, aabb2);
    case ::task::SpatialRelationship::BELOW:
      return isBelow(aabb1, aabb2);
    case ::task::SpatialRelationship::LEFT_OF:
      return isLeftOf(aabb1, aabb2);
    case ::task::SpatialRelationship::RIGHT_OF:
      return isRightOf(aabb1, aabb2);
    default:
      return false;
  }
  return false;
}

bool isInside(const b2Body& body, const b2Body& baseBody,
              const ::scene::Shape& phantomShape) {
  ::scene::Body thriftBody = createPhantomThriftBody(baseBody, phantomShape);

  for (const b2Fixture* f = body.GetFixtureList(); f; f = f->GetNext()) {
    if (f->GetType() == b2Shape::e_circle) {
      const b2CircleShape* circle = (b2CircleShape*)f->GetShape();
      ::scene::Body circleBody =
          getThriftCircleBody(body.GetPosition(), circle->m_radius);
      return isCircleInsideBody(circleBody, thriftBody);
    } else if (f->GetType() == b2Shape::e_polygon) {
      const b2PolygonShape* poly = (b2PolygonShape*)f->GetShape();
      for (size_t i = 0; i < poly->m_count; i++) {
        b2Vec2 v = geometry::translatePoint(
            poly->m_vertices[i], body.GetPosition(), body.GetAngle());
        ::scene::Vector pt;
        pt.__set_x(v.x);
        pt.__set_y(v.y);
        if (isPointInsideBody(pt, thriftBody) == false) {
          return false;
        }
      }
    }
  }
  return true;
}

bool isTouching(const b2Body& body1, const b2Body& body2) {
  size_t body2Id = getBodyId(body2);
  for (const b2ContactEdge* ce = body1.GetContactList(); ce; ce = ce->next) {
    if (body2Id == getBodyId(*ce->other) &&
        getBodyType(*ce->other) != Box2dData::USER &&
        ce->contact->IsTouching()) {
      return true;
    }
  }
  return false;
}

bool isValidRelationship(const b2Body& body1, const b2Body& body2,
                         const ::task::SpatialRelationship::type relationship,
                         const ::scene::Shape& phantomShape) {
  switch (relationship) {
    case ::task::SpatialRelationship::TOUCHING:
    case ::task::SpatialRelationship::TOUCHING_BRIEFLY:
      return isTouching(body1, body2);
    case ::task::SpatialRelationship::INSIDE:
      return isInside(body1, body2, phantomShape);
    case ::task::SpatialRelationship::NOT_TOUCHING:
      return !isTouching(body1, body2);
    case ::task::SpatialRelationship::NOT_INSIDE:
      return !isInside(body1, body2, phantomShape);
    case ::task::SpatialRelationship::NONE:
      return false;
    default:
      return checkDirectionalRelationship(body1, body2, relationship);
  }
  return false;
}

void checkTaskValidity(const ::task::Task& task) {
  bool inside = false;
  for (auto r = task.relationships.begin(); r != task.relationships.end();
       ++r) {
    if (*r == ::task::SpatialRelationship::type::INSIDE ||
        *r == ::task::SpatialRelationship::type::NOT_INSIDE) {
      inside = true;
    }
  }
  if (inside && task.__isset.phantomShape == false) {
    throw std::runtime_error(
        "Phantom body is required to evaluate INSIDE and NOT_INSIDE "
        "relationships");
  }
}

bool isTwoBallTouchingCase(
    const ::scene::Body thriftBody1, const ::scene::Body& thriftBody2,
    const std::vector<::task::SpatialRelationship::type>& relationships) {
  if (thriftBody1.shapes.size() != 1) return false;
  if (thriftBody2.shapes.size() != 1) return false;
  if (relationships.size() != 1) return false;
  if (!thriftBody1.shapes[0].__isset.circle) return false;
  if (!thriftBody2.shapes[0].__isset.circle) return false;
  if (relationships[0] != ::task::SpatialRelationship::TOUCHING) return false;
  return true;
}
}  // namespace

bool isTaskInSolvedState(const ::task::Task& task,
                         const b2WorldWithData& world) {
  checkTaskValidity(task);
  const b2Body* body1 = nullptr;
  const b2Body* body2 = nullptr;

  for (const b2Body* box2dBody = world.GetBodyList(); box2dBody != nullptr;
       box2dBody = box2dBody->GetNext()) {
    if (box2dBody->GetUserData() == nullptr) {
      throw std::runtime_error("Found a Box2d body without userdata");
    }
    Box2dData* box2d_data = static_cast<Box2dData*>(box2dBody->GetUserData());
    if (box2d_data == nullptr) {
      throw std::runtime_error(
          "Found a Box2d body with userdata that is not Box2dData");
    }
    if (box2d_data->object_type == Box2dData::GENERAL) {
      if (box2d_data->object_id == task.bodyId1) {
        body1 = box2dBody;
      } else if (box2d_data->object_id == task.bodyId2) {
        body2 = box2dBody;
      }
    }
    // Found both bodies, quit loop
    if (body1 != nullptr && body2 != nullptr) {
      break;
    }
  }

  if (body1 == nullptr || body2 == nullptr) {
    throw std::runtime_error("Task body IDs not present in the scene");
  }

  const auto& thriftBody1 = task.scene.bodies[task.bodyId1];
  const auto& thriftBody2 = task.scene.bodies[task.bodyId2];
  // A custom check for a pair of touching balls to improve stability.
  if (isTwoBallTouchingCase(thriftBody1, thriftBody2, task.relationships)) {
    const auto r1 = body1->GetFixtureList()->GetShape()->m_radius;
    const auto r2 = body2->GetFixtureList()->GetShape()->m_radius;
    const float distance = sqrt(
        geometry::squareDistance(body1->GetPosition(), body2->GetPosition()));
    return distance < r1 + r2 + kBallTouchingThreshold;
  }

  ::scene::Shape scaledPhantomShape;
  if (task.__isset.phantomShape && task.phantomShape.__isset.polygon) {
    scaledPhantomShape = p2mShape(task.phantomShape);
  }

  for (auto r = task.relationships.begin(); r != task.relationships.end();
       ++r) {
    if (isValidRelationship(*body1, *body2, *r, scaledPhantomShape) == false) {
      return false;
    }
  }
  return true;
}
