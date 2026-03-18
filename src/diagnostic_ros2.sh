#!/bin/bash

echo "🔍 Diagnostic de l'environnement ROS 2 Jazzy"
echo "============================================"

# 1. Vérification ROS 2
echo -e "\n📦 ROS 2 - Distribution et environnement"
echo "ROS_DISTRO: $ROS_DISTRO"
echo "ROS_VERSION: $ROS_VERSION"
which ros2

# 2. Présence des paquets critiques
echo -e "\n📦 Vérification des paquets nécessaires"
for pkg in ros-jazzy-rosidl-cmake ros-jazzy-rosidl-default-generators python3-colcon-common-extensions; do
  dpkg -s $pkg &>/dev/null && echo "✅ $pkg est installé" || echo "❌ $pkg manquant"
done

# 3. Présence des fichiers critiques dans le package
echo -e "\n📁 Structure du package 'commun'"
PKG_DIR=~/Projets/ROS/robot_devastator_ws/src/commun
[[ -f "$PKG_DIR/package.xml" ]] && echo "✅ package.xml trouvé" || echo "❌ package.xml manquant"
[[ -f "$PKG_DIR/CMakeLists.txt" ]] && echo "✅ CMakeLists.txt trouvé" || echo "❌ CMakeLists.txt manquant"
[[ -f "$PKG_DIR/srv/Parler.srv" ]] && echo "✅ srv/Parler.srv trouvé" || echo "❌ srv/Parler.srv manquant"

# 4. Contenu de la balise <member_of_group>
echo -e "\n🔎 Analyse de package.xml"
grep -q "<member_of_group>rosidl_interface_packages</member_of_group>" "$PKG_DIR/package.xml" \
  && echo "✅ Balise <member_of_group> correcte" \
  || echo "❌ Balise <member_of_group> absente ou incorrecte"

# 5. Compilation test
echo -e "\n🧪 Tentative de compilation avec colcon"
cd ~/Projets/ROS/robot_devastator_ws || exit 1
rm -rf build/ install/ log/
source /opt/ros/jazzy/setup.bash
colcon build --packages-select commun --symlink-install

BUILD_RESULT=$?

if [[ $BUILD_RESULT -eq 0 ]]; then
  echo -e "\n✅ Compilation réussie"
else
  echo -e "\n❌ Compilation échouée (code $BUILD_RESULT)"
fi

echo -e "\n📋 Fin du diagnostic"
