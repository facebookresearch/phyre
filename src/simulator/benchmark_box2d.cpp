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
#include <cstdio>
#include <cstdlib>

#include <cmath>
#include <functional>
#include <iostream>
#include <memory>
#include <random>
#include <thread>
#include <utility>
#include <vector>

// Multiprocessing goodies!
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

// Serialization stuff. Also mostly for multiprocessing.
#include <thrift/protocol/TBinaryProtocol.h>
#include <thrift/transport/TBufferTransports.h>

#include "gen-cpp/scene_types.h"
#include "thrift_box2d_conversion.h"
#include "utils/timer.h"

using scene::Body;
using scene::BodyType;
using scene::Polygon;
using scene::Scene;
using scene::Shape;
using scene::Vector;

using apache::thrift::protocol::TBinaryProtocol;
using apache::thrift::transport::TMemoryBuffer;

constexpr int kFps = 60;
constexpr int kBatchSize = 1024;
constexpr int kNumSteps = kFps * 10;
constexpr float32 kTimeStep = 1.0f / static_cast<float>(kFps);
constexpr int32 kVelocityIterations = 10;
constexpr int32 kPositionIterations = 10;

Body BuildBox(float x, float y, float width, float height, float angle = 0,
              bool dynamic = true) {
  Body body;
  Vector bodyPos;
  bodyPos.x = x;
  bodyPos.y = y;
  body.__set_position(bodyPos);
  body.__set_angle(angle);
  Polygon poly;
  std::vector<Vector> vertices;
  for (int i = 0; i < 4; i++) {
    Vector v;
    v.x = (0. + (i == 2 || i == 3)) * width;
    v.y = (0. + (i == 1 || i == 2)) * height;
    vertices.push_back(v);
  }
  poly.vertices = vertices;
  Shape shape;
  shape.__set_polygon(poly);
  body.__set_shapes({shape});
  body.bodyType = dynamic ? BodyType::DYNAMIC : BodyType::STATIC;
  return body;
}

int randint(int max) {
  // Generates integer in {0, 1, ..., max - 1}.
  return static_cast<int>((static_cast<double>(rand()) / RAND_MAX - 1e-6) *
                          max);
}

Scene CreateDemoScene() {
  std::vector<Body> bodies;
  bodies.push_back(BuildBox(50, 100, 20, 20));
  bodies.push_back(BuildBox(350, 100, 20, 30, 120));

  for (int i = 0; i < 5 + randint(10); ++i) {
    bodies.push_back(BuildBox(20 + 37 * i, 200 + 15 * randint(2),
                              20 - randint(15), 20 - randint(15), i * 5));
  }

  // Pendulum
  bodies.push_back(BuildBox(20, 90, 175, 5));
  bodies.push_back(BuildBox(100, 0, 5, 80, 0, false));

  const int width = 640;
  const int height = 480;
  Scene scene;
  scene.__set_width(width);
  scene.__set_height(height);
  scene.__set_bodies(bodies);
  return scene;
}

inline Scene simulate(const Scene& scene, const int32_t num_steps) {
  auto world = convertSceneToBox2dWorld(scene);
  for (int32_t i = 0; i < num_steps; i++) {
    world->Step(kTimeStep, kVelocityIterations, kPositionIterations);
  }
  return updateSceneFromWorld(scene, *world);
}

inline std::vector<Scene> simulateWithThreads(const std::vector<Scene>& scenes,
                                              const int num_steps,
                                              const size_t num_workers) {
  std::vector<Scene> newScenes(scenes.size());
  std::vector<std::thread> workers;
  std::cout << "Using thread pool with " << num_workers << " threads"
            << std::endl;
  for (size_t i = 0; i < num_workers; ++i) {
    workers.push_back(
        std::thread([&scenes, &newScenes, i, num_workers, num_steps]() {
          std::vector<Scene> local_new_scenes(scenes.size());
          for (size_t j = i; j < scenes.size(); j += num_workers) {
            local_new_scenes[j] = simulate(scenes[j], num_steps);
          }
          for (size_t j = i; j < scenes.size(); j += num_workers) {
            newScenes[j] = local_new_scenes[j];
          }
        }));
  }
  for (auto& t : workers) {
    t.join();
  }
  return newScenes;
}

void* sharedMalloc(int len) {
  void* p = mmap(0, len, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANON, -1, 0);
  if (p == (void*)-1) printf("mmap failed!\n");
  return p;
}

void sharedFree(void* p, int len) { munmap(p, len); }

Scene deserialize(const std::vector<uint8_t>& serialized) {
  std::shared_ptr<TMemoryBuffer> memoryBuffer(new TMemoryBuffer());
  std::unique_ptr<TBinaryProtocol> protocol(new TBinaryProtocol(memoryBuffer));
  memoryBuffer->resetBuffer(const_cast<uint8_t*>(serialized.data()),
                            serialized.size());
  Scene scene;
  scene.read(protocol.get());
  return scene;
}

std::vector<uint8_t> serialize(const Scene& scene) {
  std::shared_ptr<TMemoryBuffer> memoryBuffer(new TMemoryBuffer());
  std::unique_ptr<TBinaryProtocol> protocol(new TBinaryProtocol(memoryBuffer));
  scene.write(protocol.get());

  uint8_t* buffer;
  uint32_t sz;
  memoryBuffer->getBuffer(&buffer, &sz);
  return std::vector<uint8_t>(buffer, buffer + sz);
}

inline std::vector<Scene> simulateWithProcesses(
    const std::vector<Scene>& scenes, const int num_steps,
    const size_t num_workers) {
  std::vector<int> pids;

  // Assume that the sizes of scenes are not changes during simulation.
  std::vector<uint8_t*> sceneSharedBuffers;
  std::vector<size_t> bufferSizes;
  for (const auto& scene : scenes) {
    const size_t sz = serialize(scene).size();
    bufferSizes.push_back(sz);
    sceneSharedBuffers.push_back(static_cast<uint8_t*>(sharedMalloc(sz)));
  }

  std::cout << "Using " << num_workers << " processes" << std::endl;
  for (size_t i = 0; i < num_workers; ++i) {
    const int pid = fork();
    if (pid == 0) {
      // Child.
      for (size_t j = i; j < scenes.size(); j += num_workers) {
        const Scene newScene = simulate(scenes[j], num_steps);
        const std::vector<uint8_t> serializedNewScene = serialize(newScene);
        if (serializedNewScene.size() != bufferSizes[j]) {
          exit(3);
        }
        std::copy_n(serializedNewScene.data(), serializedNewScene.size(),
                    sceneSharedBuffers[j]);
      }
      exit(0);
    } else if (pid < 0) {
      // Error.
      std::cout << "FATAL: Fork failed!" << std::endl;
      exit(2);
    } else {
      // Parent.
      pids.push_back(pid);
    }
  }
  for (const int pid : pids) {
    int status;
    if (waitpid(pid, &status, 0) != -1) {
      if (WIFEXITED(status)) {
        int returned = WEXITSTATUS(status);
        if (returned != 0) {
          std::cout << "FATAL: Worker exited with failure status: " << returned
                    << std::endl;
          exit(5);
        }
      } else {
        std::cout << "FATAL: Worker died unexpectedly" << std::endl;
        exit(5);
      }
    } else {
      std::perror("FATAL: waitpid() failed");
      exit(5);
    }
  }
  std::vector<Scene> newScenes(scenes.size());
  for (size_t i = 0; i < newScenes.size(); ++i) {
    std::vector<uint8_t> serialized(sceneSharedBuffers[i],
                                    sceneSharedBuffers[i] + bufferSizes[i]);
    newScenes[i] = deserialize(serialized);
    sharedFree(sceneSharedBuffers[i], bufferSizes[i]);
  }
  return newScenes;
}

std::vector<Scene> simulateAndReport(
    std::function<std::vector<Scene>()> runSimulation,
    const std::vector<Scene>& canonicalScenes, double* rtfPtr = nullptr) {
  SimpleTimer timer;
  std::vector<Scene> newScenes = runSimulation();
  const double seconds = timer.GetSeconds();
  const double secondsPerScene = seconds / newScenes.size();
  const double rtf = kNumSteps / static_cast<float>(kFps) / secondsPerScene;
  printf("Total: %.2lfs\tPerScene:%.4lfs\tRTF: %.1lf\n", seconds,
         secondsPerScene, rtf);
  if (!canonicalScenes.empty()) {
    int fails = 0;
    for (size_t i = 0; i < newScenes.size(); ++i) {
      if (newScenes[i] != canonicalScenes[i]) {
        ++fails;
      }
    }
    if (fails) {
      std::cout << "EEE: # discrepancies: " << fails << "\n";
      exit(2);
    }
  }
  if (rtfPtr != nullptr) {
    *rtfPtr = rtf;
  }
  return newScenes;
}

int main(int argc, char** argv) {
  std::srand(1);
  std::vector<Scene> scenes;
  for (int i = 0; i < kBatchSize; ++i) {
    scenes.push_back(CreateDemoScene());
  }
  std::cout << "Total steps: " << kNumSteps * kBatchSize << "\n";

  std::cout << "\n=== Running single thread to get canonical scenes\n";
  const auto canonicalScenes = simulateAndReport(
      [scenes]() {
        std::vector<Scene> newScenes(scenes.size());
        for (size_t i = 0; i < scenes.size(); ++i) {
          newScenes[i] = simulate(scenes[i], kNumSteps);
        }
        return newScenes;
      },
      std::vector<Scene>());

  std::vector<std::pair<int, std::vector<double>>> data;
  for (int num_workers = 1; num_workers <= 128; num_workers *= 2) {
    double rtf;
    std::vector<double> rtfs;
    simulateAndReport(
        [scenes, num_workers]() {
          return simulateWithProcesses(scenes, kNumSteps, num_workers);
        },
        canonicalScenes, &rtf);
    rtfs.push_back(rtf);
    simulateAndReport(
        [scenes, num_workers]() {
          return simulateWithThreads(scenes, kNumSteps, num_workers);
        },
        canonicalScenes, &rtf);
    rtfs.push_back(rtf);
    data.push_back(std::make_pair(num_workers, rtfs));
  }

  for (const auto& row : data) {
    std::cout << row.first << ":";
    for (double rtf : row.second) {
      std::cout << "\t" << rtf;
    }
    std::cout << "\n";
  }

  return 0;
}
