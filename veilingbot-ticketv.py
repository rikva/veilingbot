#!/usr/bin/env python

import pprint
import sched
import time
import pickle
import datetime
import traceback
import os
from selenium import webdriver
import sys
from selenium.common.exceptions import ElementNotVisibleException, WebDriverException
from tv_credentials import USERNAME, PASSWORD, MY_NAME

scheduler = sched.scheduler(time.time, time.sleep)



def log(msg):
    # to avoid encoding hell:
    url = sys.argv[1]
    with open("veilingbot.log", "a") as logfile:
        try:
            logstring =  "%s [%s] : %s" % (time.ctime(), url, str(msg))
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

def begin(url):
    try:
        b = start_browser(url, browser=USE_BROWSER)
        log("Remaining seconds: %s" % get_remaining_secs(b))

#        if get_remaining_secs(b) is not None and get_remaining_secs(b) > 600:
#            wait_secs = get_remaining_secs(b) - 600
#            log("Remaining seconds: More than 600 secs: '%s'. Scheduling a restart in '%s' seconds to check again." % (get_remaining_secs(b), wait_secs))
#            datetime_of_next_action = datetime.datetime.now() + datetime.timedelta(seconds=wait_secs)
#            log("This would be around %s" % datetime_of_next_action)
#            scheduler.enter(wait_secs, 0, begin, (url,))
#            b.quit()

        if get_remaining_secs(b) is not None and get_remaining_secs(b) > 200:
            wait_secs = get_remaining_secs(b)-200
            datetime_of_next_action = datetime.datetime.now() + datetime.timedelta(seconds=wait_secs)
            log("Remaining seconds: More than 120 secs: '%s'. Scheduling a restart in '%s' seconds" % (get_remaining_secs(b), wait_secs))
            log("This would be around %s" % datetime_of_next_action)
            scheduler.enter(wait_secs, 0, begin, (url,))
            b.quit()

        elif get_remaining_secs(b) is not None:

            # Only login when the current bid is below our max price.
            if get_current_bid(b) < max_price:
                log("Current bid is lower than our max price; logging in")
                login = True
            else:
                log("Not logging in; current bid is higher than our max price.")
                login = False

            if login and not do_login(b, url):
                scheduler.enter(0, 1, begin, (url,))

            else:
                while get_remaining_secs(b) > 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()

                    global _current_bid
                    global _latest_bidder
                    global _remaining_secs

                    # Used to heck if current bid has changed
                    prev_bid = _current_bid

                    _remaining_secs = get_remaining_secs(b)
                    _current_bid = get_current_bid(b)
                    _latest_bidder = get_latest_bidder(b)

                    if prev_bid != _current_bid and _current_bid != 0 and prev_bid is not None:
                        log("User '%s' just raised the bid to '%s' on %s seconds left." % (_latest_bidder, _current_bid, _remaining_secs))


                    if _remaining_secs < 6 and _current_bid < max_price:
                        we_won = brute_force_bid(b, max_price)
                        if we_won:
                            log("Exiting!")
                            b.quit()
                            sys.exit(0)

                    time.sleep(0.5)

                else:
                    # The auction seems to be ended
                    time.sleep(5)
                    try:
                        _current_bid = get_current_bid(b)
                        _latest_bidder = get_latest_bidder(b)
                        log("Auction has ended, winning bid is '%s' by '%s'." % (_current_bid, _latest_bidder))
                        save_winning_bid(bid=_current_bid, bidder=_latest_bidder)
                    except Exception as e:
                        log("Something went wrong while determining winning bid")
                        log(e)
                        log(type(e))

                    b.quit()
                    scheduler.enter(5, 1, begin, (url,))

        elif get_remaining_secs(b) is None:
            log('Auction seems to be closed. Scheduling restart in 60 secs.')
            scheduler.enter(60, 1, begin, (url,))

        else:
            log('This should not happen.')

    except WebDriverException as e:
        log("Caught WebDriverException, the browser probably crashed. Forcing browser quit and rescheduling restart in 10 seconds.")
        log("The exception was: '%s'" % e)
        traceback.print_exc()
        try:
            b.quit()
        except: pass
        scheduler.enter(15, 1, begin, (url,))

    except Exception as e:
        log("Caught unexpected exception: '%s'. Forcing browser quit and rescheduling restart in 60 seconds." % e.message)
        log("The exception was: '%s'" % e)
        traceback.print_exc()

        try:
            b.quit()
        except: pass
        scheduler.enter(60, 1, begin, (url,))


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

def get_remaining_secs(browser):
    seconds_left = ''
    while not seconds_left.isdigit():
        countdownbox = browser.find_element_by_class_name("countdownbox")
        counter = countdownbox.text
        splitted_remaining_time = counter.split()

        if not splitted_remaining_time:
            log('Auction has ended.')
            make_screenshot(browser)
            return 0

        if len(splitted_remaining_time) == 3:
            # includes hour
            remaining_hours = int(splitted_remaining_time[0].split("uur")[0])
        elif len(splitted_remaining_time) == 2:
            # excludes hour
            remaining_hours = 0
        else:
            # something is wrong
            log("DEBUG: Could not parse splitted_remaining_time '%s', auction is probably ending." % splitted_remaining_time)

        remaining_mins = int(splitted_remaining_time[-2].split("min")[0])
        remaining_secs = int(splitted_remaining_time[-1].split("sec")[0])
        seconds_left = remaining_secs
        seconds_left += (remaining_mins * 60)
        seconds_left += ((remaining_hours * 60) * 60)
        seconds_left = int(seconds_left)
        return seconds_left

def get_current_bid(browser):
    for price in browser.find_elements_by_class_name('priceVeiling'):
        if price.is_displayed() and price.text:
            return int(price.text)


def get_latest_bidder(browser):
    div = browser.find_element_by_id("bids")
    if not div.is_displayed():
        div = browser.find_element_by_id("bidHistory")
    try:
        return ' '.join(div.find_elements_by_class_name("bidHistory")[0].text.split('\n')[2].split()[1:])
    except IndexError:
        return "unknown"


def save_winning_bid(bid, bidder):
    winning_bids[int(time.time())] = {bid: bidder}

    history = pprint.pformat(winning_bids)
    log(history)

    pickledfile = open( pickle_filename, "wb" )
    pickle.dump(winning_bids, pickledfile)
    pickledfile.close()



def do_login(browser, return_url=None):
    log('Signing in')
    email = browser.find_element_by_id("loginEmail")
    passwd = browser.find_element_by_id('loginPassword')
    button = browser.find_element_by_id('login')

    email.send_keys(USERNAME)
    passwd.send_keys(PASSWORD)
    button.click()

    counter = 0
    log('Waiting max. 30 seconds')
    while not browser.find_elements_by_id("loggedinContainer"):
        time.sleep(1)
        counter += 1
        log(counter)
        if counter > 30:
            log('Login failed.')
            return False
    else:
        log('Logged in successfully.')
        if return_url:
            log("Returning to url '%s'" % return_url)
            go_to_url(browser, return_url)
            log("Current bid is: %s" % get_current_bid(browser))
        return True

def do_place_bid(browser, price):
    log("ACTION is %s" % ACTION)
    if ACTION != "bid":
        log("We are doing a dry run. Not bidding! Creating screenshot instead.")
        make_screenshot(browser)
        return

    if int(price) > int(max_price):
        log("FAILSAFE (this should not happen): not placing bid of %s, it's higher than %s" % (price, max_price))
    else:
        log("Placing bid of '%s' euro" % price )
        ub = browser.find_element_by_id('userBid')
        # first clear the input field!
        log('DEBUG: Clearing input field')
        ub.clear()
        log('DEBUG: Sending %s to input field' % price)
        ub.send_keys(price)

        log('DEBUG: Sending ENTER to input field')
        keys = webdriver.common.keys.Keys()
        ub.send_keys(keys.ENTER)

        time.sleep(0.1)

        log('DEBUG: Clicking YES')
        yes_button = browser.find_element_by_class_name("yesButton")
        yes_button.click()

        log('DEBUG: Clicking OK')
        ok_button = browser.find_element_by_class_name("yesButtonCentered")
        ok_button.click()

        log('Placed bid for %s EUR' % price)
        time.sleep(0.2)

#        make_screenshot(browser)

def brute_force_bid(browser, max_price):
    """
    Try to win the auction with the lowest bid, under max_price.
    Automatically over-bids other bidders.
    Always increments the current bid with one.

    Returns True if we won
    Returns False if we lost

    Always assumes that we won, we need to CHECK if we may have lost.
    """

    log('Starting brute force bid with a max price of %s' % max_price)
    my_last_bid = 0

    while get_remaining_secs(browser) > 0:
        _current_bid = get_current_bid(browser)

        if _current_bid > my_last_bid and _current_bid < max_price:
                my_last_bid = _current_bid+1
                if my_last_bid <= max_price:
                    log("Placing bid of %s" % my_last_bid)
                    do_place_bid(browser, my_last_bid)
                else:
                    log("Curent bid is higher than or equal to my max price")
                    return False

        time.sleep(0.1)

    # We assume that we have won! But
    # Let's check if we have lost

    # Wait a few seconds
    log("Checking if we lost")
    time.sleep(3)
    winning_bidder = get_latest_bidder(browser)
    last_bid = get_current_bid(browser)

    log("Winning bidder: '%s'" % winning_bidder)
    log("Winning bid: '%s'" % last_bid)

    # Double confirm that we have lost, cause it means that we will begin bidding again.
    if winning_bidder != MY_NAME and last_bid != my_last_bid:
        # Too bad, it sure looks like we lost
        log("Too bad, we lost")
        return False

    # Wait... we have won!
    log("It looks like we won!")
    return True


def go_to_url(browser, url):
    log("Going to URL %s" % url)
    start_datetime = datetime.datetime.now()
    browser.get(url)
    elapsed_secs = datetime.datetime.now() - start_datetime
    log("Opening page succeeded in %s seconds." % elapsed_secs.seconds)

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


if __name__ == '__main__':
    URL = sys.argv[1]
    max_price = int(sys.argv[2])
    USE_BROWSER = sys.argv[3]
    ACTION = sys.argv[4]
    # used for checking if bid has changed
    _current_bid = None

    pickle_filename = URL.split('/')[-1] + ".pickle"

    try:
        pickledfile = open( pickle_filename, "rb" )
        winning_bids = pickle.load(pickledfile)
        pickledfile.close()
    except:
        log('No pickle file found')
        winning_bids = dict()

    scheduler.enter(0, 1, begin, (URL,))

    log('Starting scheduler')
    scheduler.run()
    log('Scheduler finished')
