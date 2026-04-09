#!/usr/bin/env bash

set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage : $0 <package_ros> [package_ros ...]"
  echo "Exemple : $0 commun robot_devastator"
  exit 1
fi

workspace_dir="$(cd "$(dirname "$0")/.." && pwd)"

for package_name in "$@"; do
  case "$package_name" in
    *[!A-Za-z0-9_]*|'')
      echo "Nom de package invalide : $package_name" >&2
      exit 1
      ;;
  esac

  package_build_dir="$workspace_dir/build/$package_name"
  package_install_dir="$workspace_dir/install/$package_name"

  if [ -d "$package_build_dir" ]; then
    rm -rf "$package_build_dir"
    echo "Supprime : $package_build_dir"
  else
    echo "Absent : $package_build_dir"
  fi

  if [ -d "$package_install_dir" ]; then
    rm -rf "$package_install_dir"
    echo "Supprime : $package_install_dir"
  else
    echo "Absent : $package_install_dir"
  fi
done

echo
echo "Relance ensuite :"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  colcon build --packages-select $*"
