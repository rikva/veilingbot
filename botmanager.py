#!/usr/bin/env python
import subprocess
from ConfigParser import SafeConfigParser
from time import sleep
import sys

parser = SafeConfigParser()
parser.read('config.cfg')

processes = []


def _slugify(url):
    for char in ['https://', 'http://', 'www.', '/', ':']:
        url = url.replace(char, "")
    return url

try:
    for section in parser.sections():
        url = parser.get(section, 'url')
        maxprice = parser.get(section, 'maxprice')
        action = parser.get(section, 'action')
        browser = parser.get(section, 'browser')

        command = "python -u veilingbot.py %s %s %s %s" % (url, maxprice, browser, action)

        logfile = _slugify(url) + ".log"
        with open(logfile, "a") as log:
            print "Starting process: %s - logging to file %s" % (command, logfile)
            processes.append(subprocess.Popen(command, stdout=log, stderr=log, shell=True))

        print "Sleeping 10 seconds."
        sleep(10)

    print "Done"

    # Start loop and check on processes
    while True:
        sleep(1)
        if not processes:
            print "No processes left, exiting"
            sys.exit(0)

        for process in processes:
            if process.poll():
                # process has died
                print "One process has died with returncode %s." % process.returncode
                processes.remove(process)

except Exception:
    print "Exception! Killing all processes..."
    for p in processes:
        p.kill()
    raise

