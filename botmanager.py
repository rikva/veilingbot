#!/usr/bin/env python
import subprocess
from ConfigParser import SafeConfigParser
from time import sleep
import sys

parser = SafeConfigParser()
parser.read('config.cfg')

processes = []

for section in parser.sections():
    url = parser.get(section, 'url')
    maxprice = parser.get(section, 'maxprice')
    action = parser.get(section, 'action')
    browser = parser.get(section, 'browser')

    command = "python veilingbot.py %s %s %s %s" % (url, maxprice, browser, action)
    print "Starting process: %s" % command
    processes.append(subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True))

# Start loop and check on processes
while True:
    sleep(1)
    if not processes:
        print "No processes left, exiting"
        sys.exit(0)

    for process in processes:
        if not process.poll():
            # process has died
            print "One process has died with returncode %s." % process.returncode
            processes.remove(process)

