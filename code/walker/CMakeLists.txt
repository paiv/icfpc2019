cmake_minimum_required(VERSION 3.1)

set(CMAKE_CXX_STANDARD 11)

project(walker)

add_library(walker SHARED program.cpp)
