CXX ?= clang++
CXXFLAGS ?= -std=c++17 -g -O2
OPENCV_CFLAGS := $(shell pkg-config --cflags opencv4 2>/dev/null || echo "-I/usr/include/opencv4")
OPENCV_CORE_LIBS := -lopencv_core -lopencv_imgproc -lopencv_features2d -lopencv_xfeatures2d -lopencv_imgcodecs -lopencv_flann
OPENCV_GUI_LIBS := -lopencv_highgui
QT6_LIBS := $(shell pkg-config --libs Qt6OpenGLWidgets Qt6Widgets Qt6OpenGL Qt6Gui Qt6DBus Qt6Test Qt6Core 2>/dev/null || echo "")

all: compute.out match.out

demo: demo.out

compute.out: compute.cpp structs.hpp
	$(CXX) $(CXXFLAGS) $(OPENCV_CFLAGS) -o $@ $< $(OPENCV_CORE_LIBS)

match.out: match.cpp structs.hpp
	$(CXX) $(CXXFLAGS) $(OPENCV_CFLAGS) -o $@ $< $(OPENCV_CORE_LIBS)

demo.out: demo.cpp structs.hpp
	$(CXX) $(CXXFLAGS) $(OPENCV_CFLAGS) -o $@ $< $(OPENCV_CORE_LIBS) $(OPENCV_GUI_LIBS) $(QT6_LIBS)

clean:
	rm -f *.out

.PHONY: all demo clean
