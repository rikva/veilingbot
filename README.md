Dependencies:

sudo apt-get install xvfb git python-pip tmux htop x11vnc


- Start Xvfb (in tmux):
# Xvfb :99 -ac

- Make sure DISPLAY and PATH are good:
# export DISPLAY=:99
# export PATH=$PATH:`pwd`

- Optional; start VNC
# mkdir ~/.x11vnc
# x11vnc -storepasswd somepassword ~/.x11vnc/passwd
# x11vnc -forever -display :99  -rfbauth ~/.x11vnc/passwd
