import pprint
import sched
import time
import pickle
from selenium import webdriver
import sys
from credentials import USERNAME, PASSWORD

scheduler = sched.scheduler(time.time, time.sleep)


def log(msg):
    # to avoid encoding hell:
    try:
        print time.ctime() + ' : ' +  str(msg)
    except:
        print time.ctime() + ' : Could not decode string!'


def make_screenshot(browser):
    filename = str(time.time()) + '.png'
    browser.get_screenshot_as_file(filename)
    log('Created screenshot: %s' % filename)

def begin(url):
    placed_bid = False
    try:
        b = start_browser(url)
        print 'get remaining secs:', get_remaining_secs(b)

        if get_remaining_secs(b) is not None and get_remaining_secs(b) > 600:
            wait_secs = get_remaining_secs(b) - 600
            log("Remaining seconds: More than 600 secs: '%s'. Scheduling a restart in '%s' seconds to check again." % (get_remaining_secs(b), wait_secs))
            scheduler.enter(wait_secs, 0, begin, (url,))
            b.quit()

        elif get_remaining_secs(b) is not None and get_remaining_secs(b) > 200:
            wait_secs = get_remaining_secs(b)-200
            log("Remaining seconds: More than 200 secs: '%s'. Scheduling a restart in '%s' seconds" % (get_remaining_secs(b), wait_secs))
            scheduler.enter(wait_secs, 0, begin, (url,))
            b.quit()

        elif get_remaining_secs(b) is not None:

            if not do_login(b, url):
                scheduler.enter(0, 1, begin, (url,))
            else:
                while get_remaining_secs(b) > 0:
                    global _current_bid
                    global _latest_bidder
                    global _remaining_secs

                    _remaining_secs = get_remaining_secs(b)
                    _current_bid = get_current_bid(b)
                    _latest_bidder = get_latest_bidder(b)

#                    max_price = 5

                    if _remaining_secs < 6 and _current_bid < max_price:
                        brute_force_bid(b, max_price)
#                        if not placed_bid:
#                            log("placing bid!")
#                            log(_remaining_secs)
#                            log(_current_bid)
#                            do_place_bid(b, 3)
#                            placed_bid = True

                    time.sleep(0.5)

                else:
                    time.sleep(5)
#                    print 'get remaining secs:', get_remaining_secs(b)
                    try:
                        _current_bid = get_current_bid(b)
                        _latest_bidder = get_latest_bidder(b)
                        log("Auction has ended, winning bid is '%s' by '%s'." % (_current_bid, _latest_bidder))
                        save_winning_bid(bid=_current_bid, bidder=_latest_bidder)
                    except Exception as e:
                        log("Something went wrong: '%s'" % e.message)

                    b.quit()
                    scheduler.enter(5, 1, begin, (url,))

        elif get_remaining_secs(b) is None:
            log('Auction seems to be closed. Scheduling restart in 60 secs.')
            scheduler.enter(60, 1, begin, (url,))

        else:
            log('This should not happen.')

    except Exception as e:
        log("Caught exception: '%s'. Rescheduling restart in 1 minute." % e.message)
	print e
	print e.message
	
        scheduler.enter(60, 1, begin, (url,))



def start_browser(url):
    log("Starting browser")
    chrome_options = webdriver.ChromeOptions()
    chrome_options._arguments = ["--user-data-dir=/home/rik/.config/google-chrome/Default/", "--incognito"]
    browser = webdriver.Chrome(chrome_options=chrome_options)
#    profile = webdriver.FirefoxProfile()
#    profile.native_events_enabled = True
#    browser = webdriver.Firefox(profile)
#    browser = webdriver.Remote("http://localhost:4444/wd/hub", webdriver.DesiredCapabilities.HTMLUNITWITHJS)
    log("Opening url '%s'" % url)
    browser.get(url)
    return browser

def get_remaining_secs(browser):
    seconds_left = ''
    while not seconds_left.isdigit():
        try:
            counter_span = browser.find_element_by_class_name('counter-running')
            celement = counter_span.find_element_by_tag_name('span')
            timestring = celement.text.split()

            if timestring[0] == 'Gesloten' or timestring[0] == '':
                log('Auction has ended.')

                make_screenshot(browser)

                return 0

            if len(timestring) == 6:
                # includes hour
                remaining_hours = int(timestring[0])
            elif len(timestring) == 4:
                # excludes hour
                remaining_hours = 0
            else:
                # something is wrong
                log("DEBUG: Could not parse timestring '%s', auction is probably ending." % timestring)

            remaining_mins = int(timestring[-4])
            remaining_secs = int(timestring[-2])
            seconds_left = remaining_secs
            seconds_left += (remaining_mins * 60)
            seconds_left += ((remaining_hours * 60) * 60)
            seconds_left = int(seconds_left)
            return seconds_left

        except Exception as e:
            log("DEBUG: '%s'" % e.message)
            log('Returning 11 seconds')
            return 11

def get_current_bid(browser):
    for i in range(10):
        try:
            for price in browser.find_elements_by_class_name('price'):
                if price.text:
                    if len(price.text.split()) == 2:
                        return int(price.text.split()[1])
                        break
                    break
        except:
            pass


def get_latest_bidder(browser):
    try:
        bh = browser.find_element_by_id('biddinghistory')
        li = bh.find_element_by_tag_name('li')
        p = li.find_element_by_tag_name('p')
        st = p.find_element_by_tag_name('strong')
        return st.text
    except:
        return 'unknown'

def save_winning_bid(bid, bidder):
#    if url not in winning_bids.keys():
#        winning_bids[url] = dict()

    winning_bids[int(time.time())] = {bid: bidder}

    pprint.pprint(winning_bids)

    pickledfile = open( pickle_filename, "wb" )
    pickle.dump(winning_bids, pickledfile)
    pickledfile.close()



def do_login(browser, return_url=None):
    log('Signing in')
    time.sleep(2)
    browser.get("https://www.vakantieveilingen.nl/login.html")
    log('Waiting 5 secs')
    time.sleep(5)

    open_login = browser.find_element_by_class_name('openLogin')
    open_login.click()

    email = browser.find_element_by_id('loginEmailField')
    passwd = browser.find_element_by_id('loginPasswordField')

    form = browser.find_element_by_id('LoginForm')
    fieldset = form.find_element_by_tag_name('fieldset')
    button = fieldset.find_elements_by_tag_name('input')[-1]

    email.send_keys(USERNAME)
    passwd.send_keys(PASSWORD)
    button.click()

    counter = 0
    log('Waiting max. 60 seconds')
    while browser.current_url != "https://www.vakantieveilingen.nl/myauctions/#":
        time.sleep(1)
        counter += 1
        log(counter)
        if counter > 60:
            log('Login failed.')
            return False
    else:
        log('Logged in successfully.')
        if return_url:
            log("Returning to url '%s'" % return_url)
            browser.get(return_url)
        return True

def do_place_bid(browser, price):
    if int(price) > int(max_price):
        log("Failsafe: not placing bid of %s, it's higher than %s" % (price, max_price))
    else:
        log("Placing bid of '%s' euro" % price )
        ub = browser.find_element_by_id('userBid')
        # first clear the input field!
        log('DEBUG: Clearing input field')
        ub.clear()
        log('DEBUG: Sending %s to input field' % price)
        ub.send_keys(price)
        bm = browser.find_element_by_id('PrototypeLoginTrigger')
        log('DEBUG: clicking PrototypeLoginTrigger button')
        bm.click()
        time.sleep(0.2)
        pb = browser.find_element_by_id('placeBidButton')
        log('DEBUG: Clicking placeBidButton')
        pb.click()
        log('Placed bid for %s EUR' % price)
        #log('DEBUG: Setting my_bid to ^ price')
        #my_bid = price
        time.sleep(0.2)
        # Try to close all dialogs:
        log('DEBUG: Closing any dialogs')
        for dialog in browser.find_elements_by_class_name('DialogClose'):
            try:
                dialog.click()
                log('Closed a dialog window.')
            except:
                log('Failed to close a dialog.')
        make_screenshot(browser)

def brute_force_bid(browser, max_price):
    log('Starting brute force bid with a max price of %s' % max_price)
    my_last_bid = 0

    while get_remaining_secs(browser) > 0:
        _remaining_secs = get_remaining_secs(browser)
        _current_bid = get_current_bid(browser)
        _latest_bidder = get_latest_bidder(browser)

        if _current_bid > my_last_bid and _current_bid < max_price:
                my_last_bid = _current_bid+1
                if my_last_bid <= max_price:
                    log("Placing bid of %s" % my_last_bid)
                    do_place_bid(browser, my_last_bid)

        time.sleep(0.1)

if __name__ == '__main__':
    url = sys.argv[1]
    max_price = int(sys.argv[2])
    pickle_filename = url.split('/')[-1] + ".pickle"

    try:
        pickledfile = open( pickle_filename, "rb" )
        winning_bids = pickle.load(pickledfile)
        pickledfile.close()
    except:
        log('No pickle file found')
        winning_bids = dict()

    scheduler.enter(0, 1, begin, (url,))

    log('Starting scheduler')
    scheduler.run()
    log('Scheduler finished')
