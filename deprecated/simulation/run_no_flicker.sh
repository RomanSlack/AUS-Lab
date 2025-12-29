#!/bin/bash

# Check which desktop environment/compositor is running
if pgrep -x "kwin_x11" > /dev/null; then
    echo "Detected KDE Plasma - disabling compositor..."
    qdbus org.kde.KWin /Compositor suspend
    COMPOSITOR="kde"
elif pgrep -x "gnome-shell" > /dev/null; then
    echo "Detected GNOME - disabling compositor..."
    gsettings set org.gnome.desktop.wm.preferences compositing false
    COMPOSITOR="gnome"
elif pgrep -x "mutter" > /dev/null; then
    echo "Detected Mutter compositor..."
    COMPOSITOR="mutter"
else
    echo "No known compositor detected - running normally"
    COMPOSITOR="none"
fi

# Activate conda environment and run simulation
echo "Starting simulation..."
source /home/roman/miniconda3/etc/profile.d/conda.sh
conda activate AegisI
python main.py --legacy-gui "$@"

# Re-enable compositor on exit
if [ "$COMPOSITOR" = "kde" ]; then
    echo "Re-enabling KDE compositor..."
    qdbus org.kde.KWin /Compositor resume
elif [ "$COMPOSITOR" = "gnome" ]; then
    echo "Re-enabling GNOME compositor..."
    gsettings set org.gnome.desktop.wm.preferences compositing true
fi

echo "Done!"
