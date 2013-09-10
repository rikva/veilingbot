import sys
import time
import datetime
import os
from selenium import webdriver

def log(msg):
    # to avoid encoding hell:
    url = sys.argv[1]
#    last_url_part = url.split("/")[-1].split(".")[0]
    last_url_part = url[-60:]
    with open("veilingbot.log", "a") as logfile:
        try:
            logstring =  "%s [%s] : %s" % (time.ctime(), last_url_part, str(msg))
            print logstring
            logfile.write(logstring+"\n")
        except:
            print time.ctime() + ' : Could not decode string!'

def make_screenshot(browser):
    # Ensure directory is created
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")

    filename = os.path.join("screenshots", str(time.time()) + '.png')
    browser.get_screenshot_as_file(filename)
    log('Created screenshot: %s' % filename)


def go_to_url(browser, url):
    log("Going to URL %s" % url)
    start_datetime = datetime.datetime.now()
    browser.get(url)
    elapsed_secs = datetime.datetime.now() - start_datetime
    log("Opening page succeeded in %s seconds." % elapsed_secs.seconds)
    close_cookie_dialogs(browser)

def close_cookie_dialogs(browser):
    try:
        # Hack to close cookie dialog, better for screenshots
        cookie_dialogs = browser.find_elements_by_class_name("acceptCookie")
        for dialog in cookie_dialogs:
            dialog.click()
            log("Closed one cookie law dialog")

        # Hack for PhantomJS which doesnt accept cookies with an empty name
        # and thus raises a dialog window which should be closed
        if browser.name == 'phantomjs':
            for dialog in browser.find_elements_by_class_name('DialogClose'):
                if dialog.is_displayed():
                    dialog.click()
                    log("Closed one cookie warning dialog")
    except:
        pass

def start_browser(url, browser="chrome"):
    log("Starting browser")

    if browser == "chrome":
        chrome_options = webdriver.ChromeOptions()
        #        chrome_options._arguments = ["--user-data-dir=/home/rik/.config/google-chrome/Default/", "--incognito"]
        chrome_options._arguments = ["--incognito"]
        browser = webdriver.Chrome(chrome_options=chrome_options)

    elif browser == "firefox":
        profile = webdriver.FirefoxProfile()
        profile.native_events_enabled = True
        browser = webdriver.Firefox(profile)

    elif browser == "phantomjs":
        browser = webdriver.PhantomJS('./phantomjs-1.9.1-linux-x86_64/bin/phantomjs')

    elif browser == "htmlunit":
        browser = webdriver.Remote("http://localhost:4444/wd/hub", webdriver.DesiredCapabilities.HTMLUNITWITHJS)

    else:
        log("Unknown browser specified")
        return

    go_to_url(browser, url)
    return browser

