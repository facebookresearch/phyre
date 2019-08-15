CMAKE_TARGET := cmake_build/Makefile
VIZ_TARGET := src/viz/build/index.html
THRIFT_JS_TARGET := src/viz/public/thrift.js
GENJS_DIR := src/viz/public/gen-js
MKFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
MKFILE_DIR := $(dir $(MKFILE_PATH))

ifeq (,$(wildcard $(GENJS_DIR)/*))
	# To avoid erros of the gen-js doesn't exist depend on compile instead.
	GENJS_DEPS := compile
else
	GENJS_DEPS := $(wildcard $(GENJS_DIR)/*) $(wildcard src/viz/public/*)
endif


.PHONY: all compile generate_tasks generate_test_tasks run_server clean test develop react_deps


all: compile generate_tasks generate_test_tasks develop $(VIZ_TARGET)

$(CMAKE_TARGET):
	git submodule init
	git submodule update
	mkdir -p cmake_build && cd cmake_build && cmake -DCMAKE_BUILD_TYPE=Release .. -DCMAKE_LIBRARY_OUTPUT_DIRECTORY=../src/python/phyre -DPYTHON_EXECUTABLE=$(shell which python)

compile: $(CMAKE_TARGET)
	make -C cmake_build -j

compile_verbose: $(CMAKE_TARGET)
	make -C cmake_build -j VERBOSE=1

xc: $(CMAKE_TARGET)
	mkdir -p xc && cd xc && cmake -DCMAKE_BUILD_TYPE=Debug -GXcode .. -DCMAKE_LIBRARY_OUTPUT_DIRECTORY=../src/python/phyre

generate_tasks: | compile
	rm -rf data/generated_tasks/tasks.pickle
	cd src/python && python -m phyre.generate_tasks $(MKFILE_DIR)/data/task_scripts/main $(MKFILE_DIR)/data/generated_tasks --save-single-pickle --with-eval-stats

generate_test_tasks: | compile
	rm -rf src/simulator/tests/test_data/task_validation/task*bin
	cd src/python && python -m phyre.generate_tasks $(MKFILE_DIR)/data/task_scripts/tests/task_validation ../simulator/tests/test_data/task_validation
	rm -rf src/simulator/tests/test_data/user_input/task*bin
	cd src/python && python -m phyre.generate_tasks $(MKFILE_DIR)/data/task_scripts/tests/user_input ../simulator/tests/test_data/user_input
	rm -rf src/simulator/tests/test_data/benchmark/task*bin
	cd src/python && python -m phyre.generate_tasks $(MKFILE_DIR)/data/task_scripts/tests/benchmark ../simulator/tests/test_data/benchmark

test: | compile generate_test_tasks
	make -C cmake_build test
	cd src/python && nosetests phyre/tests/

check_solutions: | compile
	cd src/python && python -m phyre.check_solutions

run_server: | compile $(VIZ_TARGET)
	cd src/python && python -m phyre.server

gen_egg:
	cd src/python && python setup.py egg_info

develop: | compile gen_egg $(VIZ_TARGET)

react_deps:
	cd src/viz && npm ci
	
$(THRIFT_JS_TARGET):
	wget https://raw.githubusercontent.com/apache/thrift/823474ec89355f72d3f0720ae5dacc2036d41c03/lib/js/src/thrift.js -O $(THRIFT_JS_TARGET)

$(VIZ_TARGET): src/viz/src/* $(GENJS_DEPS) $(THRIFT_JS_TARGET) | compile
	cd src/viz && npm run build

clean:
	rm -rf cmake_build src/viz/build src/python/phyre/simulator_bindings.cpython-*.so src/python/Phyre.egg-info/ $(THRIFT_JS_TARGET)
