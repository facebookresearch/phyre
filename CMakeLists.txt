cmake_minimum_required(VERSION 3.5)
project(simulator VERSION 0.0.1 LANGUAGES CXX)

###########################################
# Global flags

# For pybind11 to work on Linux.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

##############################################
# Declare dependencies
find_package(Boost 1.58 REQUIRED COMPONENTS program_options filesystem thread)
find_package(Threads REQUIRED)
find_package(pybind11 REQUIRED)

# Build GTest.
# Prevent overriding the parent project's compiler/linker
# settings on Windows
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

# Add googletest directly to our build. This defines
# the gtest and gtest_main targets.
add_subdirectory(${CMAKE_SOURCE_DIR}/third-party/googletest EXCLUDE_FROM_ALL)

# Check for math library for clip2tri.
include(CheckLibraryExists)
CHECK_LIBRARY_EXISTS(m cos "" HAVE_M_LIB)
if(HAVE_M_LIB)
  set(M_LIBRARY "m")
endif(HAVE_M_LIB)

# Thrift CPP library.
add_library(thrift STATIC IMPORTED)
set_target_properties(thrift PROPERTIES IMPORTED_LOCATION $ENV{CONDA_PREFIX}/lib/libthrift.a)
set_target_properties(thrift PROPERTIES INTERFACE_LINK_LIBRARIES Boost::program_options)
set_target_properties(thrift PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${Boost_INCLUDE_DIRS};$ENV{CONDA_PREFIX}/include")


# Box2d
set(BOX2D_SOURCE_ROOT ${CMAKE_SOURCE_DIR}/third-party/Box2D)
file(
  GLOB_RECURSE
  BOX2D_SOURCE_FILES
  LIST_DIRECTORIES false
  ${BOX2D_SOURCE_ROOT}/Box2D/Box2D/*.cpp
  )
add_library(Box2D ${BOX2D_SOURCE_FILES})
target_compile_features(Box2D PRIVATE cxx_auto_type)
target_include_directories(Box2D PUBLIC ${BOX2D_SOURCE_ROOT}/Box2D)

# Box2d Convex Hull
file(
  GLOB
  BOX2D_CH_SOURCE_FILES
  LIST_DIRECTORIES false
  third-party/Box2D/Contributions/Utilities/ConvexDecomposition/*.cpp
  )
add_library(Box2DConvexHull ${BOX2D_CH_SOURCE_FILES})
target_compile_features(Box2DConvexHull PRIVATE cxx_auto_type)
target_include_directories(
  Box2DConvexHull
  PRIVATE
  ${BOX2D_SOURCE_ROOT}/Box2D
  PUBLIC
  ${BOX2D_SOURCE_ROOT}/Box2D/Box2D
  ${BOX2D_SOURCE_ROOT}/Box2D/Box2D/Common
  ${BOX2D_SOURCE_ROOT}/Contributions/Utilities/ConvexDecomposition
  )

# Clip2Tri.
set(CLIP2TRI_SOURCE_ROOT ${CMAKE_SOURCE_DIR}/third-party/clip2tri)
set(BUILD_STATIC_LIBS ON)
set(BIN_DIR bin)
set(LIB_DIR lib)
add_subdirectory(${CLIP2TRI_SOURCE_ROOT}/poly2tri)
add_subdirectory(${CLIP2TRI_SOURCE_ROOT}/clipper)
add_library(clip2tri-static STATIC ${CLIP2TRI_SOURCE_ROOT}/clip2tri/clip2tri.cpp)
target_link_libraries(clip2tri-static PRIVATE clipper-static poly2tri-static ${M_LIBRARY})
target_include_directories(clip2tri-static PUBLIC ${CLIP2TRI_SOURCE_ROOT}/clip2tri)


##############################################
# Thrift generated targets.

set(
  THRIFT_GEN_CPP_FILES
  gen-cpp/TaskService.cpp
  gen-cpp/TaskService.h
  gen-cpp/scene_constants.cpp
  gen-cpp/scene_constants.h
  gen-cpp/scene_types.cpp
  gen-cpp/scene_types.h
  gen-cpp/shared_constants.cpp
  gen-cpp/shared_constants.h
  gen-cpp/shared_types.cpp
  gen-cpp/shared_types.h
  gen-cpp/task_constants.cpp
  gen-cpp/task_constants.h
  gen-cpp/task_types.cpp
  gen-cpp/task_types.h
)
file(GLOB THRIFT_SOURCE_FILES src/if/*.thrift)

# Note that sed that repackes the imports to use 'interface' package.
add_custom_command(
  OUTPUT
    gen-py/scene/__init__.py
    gen-py/scene/constants.py
    gen-py/scene/ttypes.py
    gen-py/shared/__init__.py
    gen-py/shared/constants.py
    gen-py/shared/ttypes.py
    gen-py/task/TaskService.py
    gen-py/task/__init__.py
    gen-py/task/constants.py
    gen-py/task/ttypes.py
  COMMAND thrift -r --gen py ${CMAKE_SOURCE_DIR}/src/if/task.thrift
  COMMAND sed -i"" "'s/\\([a-z]\\+\\).ttypes/phyre.interface.\\1.ttypes/g'" gen-py/*/*.py
  DEPENDS ${THRIFT_SOURCE_FILES}
  COMMENT "Compiling thrift for Python"
)

add_custom_command(
  OUTPUT ${THRIFT_GEN_CPP_FILES}
  COMMAND thrift -r --gen cpp ${CMAKE_SOURCE_DIR}/src/if/task.thrift
  DEPENDS ${THRIFT_SOURCE_FILES}
  COMMENT "Compiling thrift for C++"
)

add_custom_command(
  OUTPUT
    gen-js/TaskService.js
    gen-js/scene_types.js
    gen-js/shared_types.js
    gen-js/task_types.js
  COMMAND thrift -r --gen js ${CMAKE_SOURCE_DIR}/src/if/task.thrift
  DEPENDS ${THRIFT_SOURCE_FILES}
  COMMENT "Compiling thrift for JS"
)

# Create dummy targets to wrap custom commands.
add_custom_target(thrift-gen-py ALL DEPENDS gen-py/scene/__init__.py)
add_custom_target(thrift-gen-cpp ALL DEPENDS gen-cpp/TaskService.cpp)
add_custom_target(thrift-gen-js ALL DEPENDS gen-js/TaskService.js)


##############################################
# Create target and set properties

# Compile cpp thrift stuff.
add_library(thrift_task ${THRIFT_GEN_CPP_FILES})
target_link_libraries(thrift_task PUBLIC thrift)
target_include_directories(thrift_task PUBLIC ${CMAKE_CURRENT_BINARY_DIR})
target_compile_features(thrift_task PRIVATE cxx_auto_type)

# Logger lib.
add_library(logger src/simulator/utils/logger)
target_link_libraries(logger PUBLIC thrift_task)
target_include_directories(logger PUBLIC src/simulator/utils)  # Propagage include dirs. # FIXME: use relative to root pathes instead.
target_compile_features(logger PRIVATE cxx_auto_type)

# Task IO.
add_library(task_io src/simulator/task_io)
target_link_libraries(task_io PUBLIC thrift_task Boost::filesystem)
target_compile_features(task_io PRIVATE cxx_auto_type)

# The main library.
add_library(
  simulator_lib
  src/simulator/creator
  src/simulator/geometry
  src/simulator/image_to_box2d
  src/simulator/task_utils
  src/simulator/task_utils_parallel
  src/simulator/task_validation
  src/simulator/thrift_box2d_conversion
  src/simulator/utils/timer
)
target_link_libraries(
  simulator_lib
  PUBLIC Box2D thrift_task
  PRIVATE Box2DConvexHull clip2tri-static logger)

target_include_directories(simulator_lib PUBLIC ${CLIP2TRI_SOURCE_ROOT}/clipper)
target_compile_features(simulator_lib PRIVATE cxx_auto_type)

# # Threading benchmark binary.
# add_executable(benchmark_box2d src/simulator/benchmark_box2d)
# target_compile_features(benchmark_box2d PRIVATE cxx_auto_type)
# target_link_libraries(benchmark_box2d PRIVATE simulator_lib Threads::Threads)
#
# # User input vectorization and simulation benchmark.
# add_executable(benchmark_user_input_box2d src/simulator/benchmark_user_input_box2d)
# target_compile_features(benchmark_user_input_box2d PRIVATE cxx_auto_type)
# target_link_libraries(benchmark_user_input_box2d PRIVATE simulator_lib task_io)

# Pybind11 binding.
pybind11_add_module(simulator_bindings src/simulator/simulator_bindings)
target_link_libraries(simulator_bindings PRIVATE thrift_task simulator_lib)
target_compile_features(simulator_bindings PRIVATE cxx_std_14)


##########################################
# Tests

include(GoogleTest)
enable_testing()

# Task solution validation.
add_executable(task_validation_test src/simulator/tests/test_task_validation.cpp)
target_link_libraries(task_validation_test task_io simulator_lib gtest_main)
target_include_directories(task_validation_test PRIVATE src/simulator)
target_compile_features(task_validation_test PRIVATE cxx_auto_type)
gtest_add_tests(TARGET task_validation_test WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

# Geometry.
add_executable(geometry_test src/simulator/tests/test_geometry.cpp)
target_link_libraries(geometry_test simulator_lib gtest_main)
target_include_directories(geometry_test PRIVATE src/simulator)
target_compile_features(geometry_test PRIVATE cxx_auto_type)
gtest_add_tests(TARGET geometry_test WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

# Simulation + box2d-and-back-conversion.
add_executable(backend_test src/simulator/tests/test_backend.cpp)
target_link_libraries(backend_test simulator_lib logger task_io gtest_main)
target_include_directories(backend_test PRIVATE src/simulator)
target_compile_features(backend_test PRIVATE cxx_auto_type)
gtest_add_tests(TARGET backend_test WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

# User input vectorization.
add_executable(user_input_test src/simulator/tests/test_user_input.cpp)
target_link_libraries(user_input_test simulator_lib task_io gtest_main)
target_include_directories(user_input_test PRIVATE src/simulator)
target_compile_features(user_input_test PRIVATE cxx_auto_type)
gtest_add_tests(TARGET user_input_test WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

# Multi process simluation.
add_executable(parallel_simulation_test src/simulator/tests/test_parallel_simulation.cpp)
target_link_libraries(parallel_simulation_test simulator_lib gtest_main)
target_include_directories(parallel_simulation_test PRIVATE src/simulator)
target_compile_features(parallel_simulation_test PRIVATE cxx_auto_type)
gtest_add_tests(TARGET parallel_simulation_test WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
