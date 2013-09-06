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


- Add hosts like facebook to hostsfile to speed up browser starts and decrease bandwidth usage
127.0.1.2       connect.facebook.com facebook.com www.facebook.com apis.google.com google-analytics.com www.google-analytics.com plus.google.com
127.0.1.3       cdn1.vakantieveilingen.nl cdn2.vakantieveilingen.nl cdn3.vakantieveilingne.nl cdn4.vakantieveilingen.nl
127.0.1.4       static1.vakantieveilingen.nl static2.vakantieveilingen.nl static3.vakantieveilingen.nl static4.vakantieveilingen.nl
