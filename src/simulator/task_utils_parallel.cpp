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
#include "gen-cpp/scene_types.h"
#include "gen-cpp/task_types.h"
#include "task_utils.h"

#include <algorithm>
#include <iostream>
#include <vector>

// Multiprocessing goodies!
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

// Serialization stuff. Also mostly for multiprocessing.
#include <thrift/protocol/TBinaryProtocol.h>
#include <thrift/transport/TBufferTransports.h>

using apache::thrift::protocol::TBinaryProtocol;
using apache::thrift::transport::TMemoryBuffer;

namespace {
void* sharedMalloc(int len) {
  void* p = mmap(0, len, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANON, -1, 0);
  if (p == (void*)-1) printf("mmap failed!\n");
  return p;
}

void sharedFree(void* p, int len) { munmap(p, len); }

::scene::Scene deserialize(const std::vector<uint8_t>& serialized) {
  std::shared_ptr<TMemoryBuffer> memoryBuffer(new TMemoryBuffer());
  std::unique_ptr<TBinaryProtocol> protocol(new TBinaryProtocol(memoryBuffer));
  memoryBuffer->resetBuffer(const_cast<uint8_t*>(serialized.data()),
                            serialized.size());
  ::scene::Scene scene;
  scene.read(protocol.get());
  return scene;
}

std::vector<uint8_t> serialize(const ::scene::Scene& scene) {
  std::shared_ptr<TMemoryBuffer> memoryBuffer(new TMemoryBuffer());
  std::unique_ptr<TBinaryProtocol> protocol(new TBinaryProtocol(memoryBuffer));
  scene.write(protocol.get());

  uint8_t* buffer;
  uint32_t sz;
  memoryBuffer->getBuffer(&buffer, &sz);
  return std::vector<uint8_t>(buffer, buffer + sz);
}

struct SerializedTaskSimulation {
  uint8_t* scenes;
  uint8_t* solvedStates;
  uint8_t* isSolution;
  int* actualNumSteps;
  int* stepsSimulated;
};
}  // namespace

std::vector<::task::TaskSimulation> simulateTasksInParallel(
    const std::vector<::task::Task>& tasks, const int num_workers,
    const int num_steps, const int stride) {
  if (num_workers <= 0) {
    // Run single-process version.
    std::vector<::task::TaskSimulation> simulations;
    for (const ::task::Task& task : tasks) {
      simulations.push_back(simulateTask(task, num_steps, stride));
    }
    return simulations;
  }

  std::vector<int> pids;

  // We need to create a shared memory where simulation results will be
  // written. The size of the buffer should be static. So we assume that the
  // sizes of scenes do not change during simulation, we need space for all
  // objects fields in TaskSimulation up to num_steps plus the actual number of
  // steps that were simulated until solution.
  // sharedBuffers layout looks likes the following:
  //   SerializedScene scenes[num_steps];
  //   bool solvedStates[num_steps];
  //   bool isSolution;
  //   int actualNumSteps;
  //   int stepsSimulated;
  std::vector<uint8_t*> sharedBuffers;
  std::vector<SerializedTaskSimulation> sharedBufferLayouts;
  std::vector<size_t> sceneSizes;
  std::vector<size_t> bufferSizes;
  for (const auto& task : tasks) {
    const size_t sceneSize = serialize(task.scene).size();
    const size_t sz =
        (sceneSize + sizeof(uint8_t)) * num_steps + sizeof(uint8_t) * 2;
    sceneSizes.push_back(sceneSize);
    bufferSizes.push_back(sz);
    sharedBuffers.push_back(static_cast<uint8_t*>(sharedMalloc(sz)));
    SerializedTaskSimulation layout;
    layout.scenes = sharedBuffers.back();
    layout.solvedStates = layout.scenes + num_steps * sceneSizes.back();
    layout.isSolution = layout.solvedStates + num_steps * sizeof(bool);
    layout.actualNumSteps =
        reinterpret_cast<int*>(layout.isSolution + sizeof(bool));
    layout.stepsSimulated =
        reinterpret_cast<int*>(layout.actualNumSteps + sizeof(int));
    sharedBufferLayouts.push_back(layout);
  }

  for (size_t workerId = 0; workerId < num_workers; ++workerId) {
    const int pid = fork();
    if (pid == 0) {
      // Worker. Run simulations and save to the shared buffer.
      for (size_t taskId = workerId; taskId < tasks.size();
           taskId += num_workers) {
        const ::task::TaskSimulation simulation =
            simulateTask(tasks[taskId], num_steps, stride);
        const int actualNumSteps = simulation.sceneList.size();
        const SerializedTaskSimulation& layout = sharedBufferLayouts[taskId];
        for (size_t step = 0; step < actualNumSteps; ++step) {
          const ::scene::Scene& scene = simulation.sceneList[step];
          const std::vector<uint8_t> serializedScene = serialize(scene);
          if (serializedScene.size() != sceneSizes[taskId]) {
            exit(3);
          }
          std::copy_n(serializedScene.data(), serializedScene.size(),
                      layout.scenes + sceneSizes[taskId] * step);
        }
        for (size_t step = 0; step < actualNumSteps; ++step) {
          layout.solvedStates[step] =
              static_cast<uint8_t>(simulation.solvedStateList[step]);
        }
        *layout.isSolution = static_cast<uint8_t>(simulation.isSolution);
        *layout.actualNumSteps = actualNumSteps;
        *layout.stepsSimulated = simulation.stepsSimulated;
      }
      exit(0);
    } else if (pid < 0) {
      // Error.
      std::cout << "FATAL: Fork failed!" << std::endl;
      exit(2);
    } else {
      // Parent. Save pid and carry on.
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
  std::vector<::task::TaskSimulation> simulationBatch(tasks.size());
  for (size_t i = 0; i < simulationBatch.size(); ++i) {
    const SerializedTaskSimulation& layout = sharedBufferLayouts[i];
    const int actualNumSteps = *layout.actualNumSteps;
    std::vector<::scene::Scene> scenes(actualNumSteps);
    for (int step = 0; step < actualNumSteps; ++step) {
      const uint8_t* start = layout.scenes + sceneSizes[i] * step;
      scenes[step] =
          deserialize(std::vector<uint8_t>(start, start + sceneSizes[i]));
    }
    const std::vector<bool> solvedStates(
        reinterpret_cast<bool*>(layout.solvedStates),
        reinterpret_cast<bool*>(layout.solvedStates + actualNumSteps));
    const bool solved = *layout.isSolution;
    simulationBatch[i].__set_sceneList(scenes);
    simulationBatch[i].__set_solvedStateList(solvedStates);
    simulationBatch[i].__set_isSolution(solved);
    simulationBatch[i].__set_stepsSimulated(*layout.stepsSimulated);

    sharedFree(sharedBuffers[i], bufferSizes[i]);
  }
  return simulationBatch;
}
