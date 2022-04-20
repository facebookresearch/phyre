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
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <chrono>
#include <memory>
#include <vector>

#include <thrift/protocol/TBinaryProtocol.h>
#include <thrift/transport/TBufferTransports.h>

#include "creator.h"
#include "gen-cpp/scene_types.h"
#include "gen-cpp/task_types.h"
#include "image_to_box2d.h"
#include "task_utils.h"
#include "thrift_box2d_conversion.h"
#include "utils/timer.h"

using ::apache::thrift::protocol::TBinaryProtocol;
using ::apache::thrift::transport::TMemoryBuffer;
using ::scene::Image;
using ::scene::Scene;
using ::scene::UserInput;
using ::scene::UserInputStatus;
using ::task::Task;
using ::task::TaskSimulation;
namespace py = pybind11;

namespace {

template <class T>
T deserialize(const py::bytes &serializedBytes) {
  py::buffer_info info(py::buffer(serializedBytes).request());
  const unsigned char *data = reinterpret_cast<const unsigned char *>(info.ptr);
  size_t length = static_cast<size_t>(info.size);

  std::shared_ptr<TMemoryBuffer> memoryBuffer(new TMemoryBuffer());
  std::unique_ptr<TBinaryProtocol> protocol(new TBinaryProtocol(memoryBuffer));
  memoryBuffer->resetBuffer(const_cast<unsigned char *>(data), length);
  T object;
  object.read(protocol.get());
  return object;
}

template <class T>
py::bytes serialize(const T &object) {
  std::shared_ptr<TMemoryBuffer> memoryBuffer(new TMemoryBuffer());
  std::unique_ptr<TBinaryProtocol> protocol(new TBinaryProtocol(memoryBuffer));
  object.write(protocol.get());

  unsigned char *buffer;
  uint32_t sz;
  memoryBuffer->getBuffer(&buffer, &sz);
  return py::bytes(reinterpret_cast<const char *>(buffer), sz);
}

UserInput buildUserInputObject(
    const py::array_t<int32_t> &points,
    const std::vector<float> &rectangulars_vertices_flatten,
    const std::vector<float> &balls_flatten) {
  if (points.ndim() != 2) {
    throw std::runtime_error("Number of dimensions must be two");
  }
  if (points.shape(1) != 2) {
    throw std::runtime_error("Second dimension must have size 2 (x, y)");
  }
  UserInput user_input;
  user_input.flattened_point_list.reserve(points.shape(0) * 2);
  auto pointsUnchecked = points.unchecked<2>();
  for (size_t i = 0; i < points.shape(0); ++i) {
    user_input.flattened_point_list.push_back(pointsUnchecked(i, 0));
    user_input.flattened_point_list.push_back(pointsUnchecked(i, 1));
  }

  for (int i = 0; i < rectangulars_vertices_flatten.size(); i += 8) {
    ::scene::AbsoluteConvexPolygon polygon;
    for (int j = 0; j < 4; j += 2) {
      polygon.vertices.push_back(
          getVector(rectangulars_vertices_flatten[i + j],
                    rectangulars_vertices_flatten[i + j + 1]));
    }
    user_input.polygons.push_back(polygon);
  }
  for (int i = 0; i < balls_flatten.size();) {
    ::scene::CircleWithPosition circle;
    circle.position.__set_x(balls_flatten[i++]);
    circle.position.__set_y(balls_flatten[i++]);
    circle.__set_radius(balls_flatten[i++]);
    user_input.balls.push_back(circle);
  }

  return user_input;
}

void addUserInputToScene(const UserInput &user_input,
                         bool keep_space_around_bodies, bool allow_occlusions,
                         ::scene::Scene *scene) {
  std::vector<::scene::Body> user_input_bodies;
  const bool good = mergeUserInputIntoScene(
      user_input, scene->bodies, keep_space_around_bodies, allow_occlusions,
      scene->height, scene->width, &user_input_bodies);
  scene->__set_user_input_status(good ? UserInputStatus::NO_OCCLUSIONS
                                      : UserInputStatus::HAD_OCCLUSIONS);
  scene->__set_user_input_bodies(user_input_bodies);
}

int getNumObjectsInScene(const Scene &scene) {
  int numObjects = 0;
  std::vector<::scene::Body> bodies = scene.bodies;
  bodies.insert(bodies.end(), scene.user_input_bodies.begin(),
                scene.user_input_bodies.end());
  for (::scene::Body &body : bodies) {
    if (body.shapeType != ::scene::ShapeType::UNDEFINED) {
      ++numObjects;
    }
  }
  return numObjects;
}

int getNumObjects(const TaskSimulation &simulation) {
  const auto &scenes = simulation.sceneList;
  if (scenes.empty()) {
    return 0;
  }
  return getNumObjectsInScene(simulation.sceneList[0]);
}

bool hadSimulationOcclusions(const TaskSimulation &simulation) {
  const auto &scenes = simulation.sceneList;
  return scenes.empty()
             ? false
             : scenes[0].user_input_status == UserInputStatus::HAD_OCCLUSIONS;
}

auto magic_ponies(const py::bytes &serialized_task, const UserInput &user_input,
                  bool keep_space_around_bodies, int steps, int stride,
                  bool need_images, bool need_featurized_objects) {
  SimpleTimer timer;
  Task task = deserialize<Task>(serialized_task);
  addUserInputToScene(user_input, keep_space_around_bodies,
                      /*allow_occlusions=*/false, &task.scene);
  auto simulation = simulateTask(task, steps, stride);

  const double simulation_seconds = timer.GetSeconds();
  const bool isSolved = simulation.isSolution;
  const bool hadOcclusions = hadSimulationOcclusions(simulation);

  const int numImagesTotal = need_images ? simulation.sceneList.size() : 0;
  const int numScenesTotal =
      need_featurized_objects ? simulation.sceneList.size() : 0;

  const int imageSize = task.scene.width * task.scene.height;
  uint8_t *packedImages = new uint8_t[imageSize * numImagesTotal];
  if (numImagesTotal > 0) {
    int writeIndex = 0;
    for (const Scene &scene : simulation.sceneList) {
      renderTo(scene, packedImages + writeIndex);
      writeIndex += imageSize;
    }
  }

  const int numSceneObjects = getNumObjects(simulation);
  float *packedVectorizedBodies =
      new float[numSceneObjects * kObjectFeatureSize * numScenesTotal];
  if (numScenesTotal > 0) {
    int writeIndex = 0;
    for (const Scene &scene : simulation.sceneList) {
      featurizeScene(scene, packedVectorizedBodies + writeIndex);
      writeIndex += kObjectFeatureSize * numSceneObjects;
    }
  }

  // Create a Python object that will free the allocated
  // memory when destroyed:
  py::capsule freeImagesWhenDone(packedImages, [](void *f) {
    auto *foo = reinterpret_cast<uint8_t *>(f);
    delete[] foo;
  });
  py::capsule freeObjectsWhenDone(packedVectorizedBodies, [](void *f) {
    auto *foo = reinterpret_cast<float *>(f);
    delete[] foo;
  });
  auto packedImagesArray =
      py::array_t<uint8_t>({numImagesTotal * imageSize},  // shape
                           {sizeof(uint8_t)}, packedImages, freeImagesWhenDone);
  auto packedObjectsArray = py::array_t<float>(
      {numScenesTotal * numSceneObjects * kObjectFeatureSize},  // shape
      {sizeof(float)}, packedVectorizedBodies, freeObjectsWhenDone);
  const double pack_seconds = timer.GetSeconds();
  return std::make_tuple(isSolved, hadOcclusions, packedImagesArray,
                         packedObjectsArray, numSceneObjects,
                         simulation_seconds, pack_seconds);
}
}  // namespace

PYBIND11_MODULE(simulator_bindings, m) {
  m.doc() = "Task simulation and validation library";

  // Expose some constants.
  m.attr("FPS") = kFps;
  m.attr("OBJECT_FEATURE_SIZE") = kObjectFeatureSize;
  m.attr("DEFAULT_MAX_STEPS") = kMaxSteps;
  m.attr("STEPS_FOR_SOLUTION") = kStepsForSolution;

  m.def(
      "simulate_scene",
      [](const py::bytes &scene, int steps) {
        const std::vector<Scene> scenes =
            simulateScene(deserialize<Scene>(scene), steps);
        std::vector<py::bytes> serializedScenes(scenes.size());
        for (size_t i = 0; i < scenes.size(); ++i) {
          serializedScenes[i] = serialize(scenes[i]);
        }
        return serializedScenes;
      },
      "Get per-frame results of scene simulation");

  m.def(
      "add_user_input_to_scene",
      [](const py::bytes &scene_serialized,
         const py::bytes &user_input_serialized, bool keep_space_around_bodies,
         bool allow_occlusions) {
        Scene scene = deserialize<Scene>(scene_serialized);
        const auto user_input = deserialize<UserInput>(user_input_serialized);
        addUserInputToScene(user_input, keep_space_around_bodies,
                            allow_occlusions, &scene);
        return serialize(scene);
      },
      "Convert user input to user_input_bodies in the scene");

  m.def(
      "check_for_occlusions",
      [](const py::bytes &serialized_task, py::array_t<int32_t> points,
         const std::vector<float> &rectangulars_vertices_flatten,
         const std::vector<float> &balls_flatten,
         bool keep_space_around_bodies) {
        const auto user_input = buildUserInputObject(
            points, rectangulars_vertices_flatten, balls_flatten);
        Task task = deserialize<Task>(serialized_task);
        addUserInputToScene(user_input, keep_space_around_bodies,
                            /*allow_occlusions=*/false, &task.scene);
        return task.scene.user_input_status == UserInputStatus::HAD_OCCLUSIONS;
      },
      "Check whether point occludes occludes scene objects");

  m.def(
      "check_for_occlusions_general",
      [](const py::bytes &serialized_task,
         const py::bytes &serialized_user_input,
         bool keep_space_around_bodies) {
        const auto user_input = deserialize<UserInput>(serialized_user_input);
        Task task = deserialize<Task>(serialized_task);
        addUserInputToScene(user_input, keep_space_around_bodies,
                            /*allow_occlusions=*/false, &task.scene);
        return task.scene.user_input_status == UserInputStatus::HAD_OCCLUSIONS;
      },
      "Check whether point occludes occludes scene objects");

  m.def(
      "simulate_task",
      [](const py::bytes &task, int steps, int stride) {
        const TaskSimulation results =
            simulateTask(deserialize<Task>(task), steps, stride);
        return serialize(results);
      },
      "Produce TaskSimulation");

  m.def(
      "magic_ponies",
      [](const py::bytes &serialized_task, py::array_t<int32_t> points,
         const std::vector<float> &rectangulars_vertices_flatten,
         const std::vector<float> &balls_flatten, bool keep_space_around_bodies,
         int steps, int stride, bool need_images,
         bool need_featurized_objects) {
        const UserInput user_input = buildUserInputObject(
            points, rectangulars_vertices_flatten, balls_flatten);
        return magic_ponies(serialized_task, user_input,
                            keep_space_around_bodies, steps, stride,
                            need_images, need_featurized_objects

        );
      },
      "Runs simulation for a batch of tasks and inputs and returns a list of"
      " isSolved statuses, list of hadOcclusion statuses, number of steps"
      " within each simulation, packed flatten array of images and timing"
      " info.");

  m.def(
      "magic_ponies_general",
      [](const py::bytes &serialized_task,
         const py::bytes &serialized_user_input,

         bool keep_space_around_bodies, int steps, int stride, bool need_images,
         bool need_featurized_objects) {
        return magic_ponies(serialized_task,
                            deserialize<UserInput>(serialized_user_input),
                            keep_space_around_bodies, steps, stride,
                            need_images, need_featurized_objects

        );
      },
      "Runs simulation for a batch of tasks and inputs and returns a list of"
      " isSolved statuses, list of hadOcclusion statuses, number of steps"
      " within each simulation, packed flatten array of images and timing"
      " info.");

  m.def(
      "render",
      [](const py::bytes &scene) {
        const Scene sceneObj = deserialize<Scene>(scene);
        std::vector<uint8_t> pixels(sceneObj.width * sceneObj.height);
        renderTo(sceneObj, pixels.data());
        return pixels;
      },
      "Produce Image");

  m.def(
      "featurize_scene",
      [](const py::bytes &scene) {
        const Scene sceneObj = deserialize<Scene>(scene);
        int numObjects = getNumObjectsInScene(sceneObj);
        std::vector<float> objectsFeaturized(numObjects * kObjectFeatureSize);
        featurizeScene(sceneObj, objectsFeaturized.data());
        return objectsFeaturized;
      },
      "Convert Scene to featurized matrix of object vectors");

  // This function is left here to suppress odd weak-reference warning in
  // Thrift. It's not doing anything useful.
  m.def(
      "DEPRECATED",
      [](const std::vector<std::vector<unsigned char>> &tasks,
         std::vector<py::array_t<int32_t>> points,
         bool keep_space_around_bodies, int num_workers, int steps) {
        std::vector<Task> tasksWithInputs;
        auto simulations = simulateTasksInParallel(tasksWithInputs, num_workers,
                                                   steps, /*stride=*/-1);
        std::vector<bool> isSolved;
        return isSolved;
      },
      "");
}
