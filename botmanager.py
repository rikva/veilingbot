#!/usr/bin/env python
import subprocess
from ConfigParser import SafeConfigParser
from time import sleep
import sys
import signal

PROCESSES = []


def _slugify(url):
    for char in ['https://', 'http://', 'www.', '/', ':']:
        url = url.replace(char, "")
    return url

def kill_processes():
    global PROCESSES

    print "Killing all subprocesses"
    for p in PROCESSES:
        p.kill()
    PROCESSES = []

def signal_handler_sigint(signal, frame):
    print "Caught CTRL+C"
    kill_processes()
    sys.exit(0)

def signal_handler_sighup(signal, frame):
    print "Reloading..."
    kill_processes()
    main()

signal.signal(signal.SIGINT, signal_handler_sigint)
signal.signal(signal.SIGHUP, signal_handler_sighup)

def main():
    try:
        parser = SafeConfigParser()
        parser.read('config.cfg')
        for section in parser.sections():
            url = parser.get(section, 'url')
            maxprice = parser.get(section, 'maxprice')
            action = parser.get(section, 'action')
            browser = parser.get(section, 'browser')

            command = "python -u veilingbot.py %s %s %s %s" % (url, maxprice, browser, action)

            logfile = _slugify(url) + ".log"
            with open(logfile, "a") as log:
                print "Starting process: %s - logging to file %s" % (command, logfile)
                PROCESSES.append(subprocess.Popen(command, stdout=log, stderr=log, shell=True))

            print "Sleeping 10 seconds."
            sleep(10)

        print "Done"

        # Start loop and check on processes & signals
        while True:
            sleep(1)
            if not PROCESSES:
                print "No processes left, exiting"
                sys.exit(0)

            for process in PROCESSES:
                if process.poll():
                    # process has died
                    print "One process has died with returncode %s." % process.returncode
                    PROCESSES.remove(process)

    except Exception:
        print "Exception! Killing all processes..."
        kill_processes()
        raise

if __name__ == "__main__":
    main()
