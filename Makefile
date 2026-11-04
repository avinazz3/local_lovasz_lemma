CXX ?= c++
CXXFLAGS ?= -O3 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic

.PHONY: all test benchmark clean sanitize
all: build/ramsey_experiment

build/ramsey_experiment: src/ramsey.cpp Makefile
	mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@
	printf '%s\n' '$(CXX) $(CXXFLAGS) src/ramsey.cpp -o build/ramsey_experiment' > build/build_command.txt

test: all build/ramsey_no_pruning
	python3 tests/test_experiment.py build/ramsey_experiment
	python3 -m unittest discover -s tests -p 'test_statistics.py'

build/ramsey_no_pruning: src/ramsey.cpp Makefile
	mkdir -p build
	$(CXX) $(CXXFLAGS) -DRAMSEY_NO_CARDINALITY_PRUNING $< -o $@

benchmark: all
	python3 scripts/benchmark.py

sanitize:
	mkdir -p build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/ramsey.cpp -o build/ramsey_sanitize
	python3 tests/test_experiment.py build/ramsey_sanitize

clean:
	rm -rf build
