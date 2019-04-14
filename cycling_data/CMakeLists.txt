cmake_minimum_required(VERSION 3.14)
project(extension-functions)
find_package (SQLite3 REQUIRED)
# Set source directory
set(SOURCE_DIR "sqlite_extensions")
# Tell CMake that headers are also in SOURCE_DIR
include_directories(${SOURCE_DIR})
set(SOURCES "${SOURCE_DIR}/extension-functions.c")

add_library(extension-functions SHARED ${SOURCES})
set_target_properties(extension-functions
  PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
  )
