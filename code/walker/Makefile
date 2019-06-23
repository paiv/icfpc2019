
.PHONY: all release debug clean

all: release

release: CMAKE_ARGS=-DCMAKE_BUILD_TYPE=Release
release: TARGET_DIR=build/release

debug: CMAKE_ARGS=-DCMAKE_BUILD_TYPE=Debug
debug: TARGET_DIR=build/debug

release debug: program

program: $(TARGET_DIR)/program
.PHONY: program

$(TARGET_DIR)/program: $(wildcard *.cpp) $(wildcard *.h) $(TARGET_DIR)/Makefile
	cd $(TARGET_DIR) && $(MAKE)

$(TARGET_DIR)/Makefile:
	echo $0
	mkdir -p $(TARGET_DIR) \
		&& cd $(TARGET_DIR) \
		&& cmake $(CMAKE_ARGS) ../..


clean:
	[ -d build ] && rm -r build
