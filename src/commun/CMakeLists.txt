cmake_minimum_required(VERSION 3.8)
project(commun)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

message(STATUS "Package.xml location: ${CMAKE_CURRENT_SOURCE_DIR}/package.xml")

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/Parler.srv" 
)

ament_package()
