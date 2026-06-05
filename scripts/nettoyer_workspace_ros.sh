#!/usr/bin/env bash

set -eu

workspace_dir="$(cd "$(dirname "$0")/.." && pwd)"

echo "Nettoyage complet du workspace ROS 2 :"
echo "  $workspace_dir/build"
echo "  $workspace_dir/install"
echo "  $workspace_dir/log"
echo

rm -rf "$workspace_dir/build" "$workspace_dir/install" "$workspace_dir/log"

echo "Nettoyage terminé."
echo
echo "Relance ensuite un build complet :"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  colcon build --symlink-install"
echo "  source install/setup.bash"