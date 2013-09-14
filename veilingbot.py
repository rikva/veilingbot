#!/usr/bin/env python
import pprint
import sched
import time
import datetime
import sys
import traceback
import sqlite3
from selenium.common.exceptions import  WebDriverException
from credentials import MY_NAME
from ticketveiling import TicketVeiling
from vakantieveilingen import VakantieVeilingen
from veilingbotcore import log, start_browser, close_cookie_dialogs

scheduler = sched.scheduler(time.time, time.sleep)


def begin(url):
    try:
        if "vakantieveilingen.nl" in url:
            log("Using VakantieVeilingen engine")
            Site = VakantieVeilingen
        elif "ticketveiling.nl" in url:
            log("Using TicketVeiling engine")
            Site = TicketVeiling
        else:
            print "Cannot detect URL"
            sys.exit(1)

        browser = start_browser(url, browser=USE_BROWSER)
        SITE = Site(browser=browser, max_price=max_price, action=ACTION)

        log("Remaining seconds: %s" % SITE.get_remaining_secs())

        if SITE.get_remaining_secs() is not None and SITE.get_remaining_secs() > 200:
            wait_secs = SITE.get_remaining_secs()-200
            datetime_of_next_action = datetime.datetime.now() + datetime.timedelta(seconds=wait_secs)
            log("Remaining seconds: More than 120 secs: '%s'. Scheduling a restart in '%s' seconds" %
                (SITE.get_remaining_secs(), wait_secs))
            log("This would be around %s" % datetime_of_next_action)
            scheduler.enter(wait_secs, 0, begin, (url,))
            browser.quit()

        elif SITE.get_remaining_secs() is not None:

            # Only login when the current bid is below our max price.
            if SITE.get_current_bid() < max_price:
                log("Current bid (%s) is lower than our max price (%s); logging in"
                    % (SITE.get_current_bid(), max_price))
                login = True
            else:
                log("Not logging in; current bid (%s) is higher than our max price (%s)."
                    %(SITE.get_current_bid(), max_price))
                login = False

            if login and not SITE.do_login():
                scheduler.enter(0, 1, begin, (url,))

            else:
                # Close cookie dialog that might have re-appeared after signing in
                close_cookie_dialogs(browser)

                while SITE.get_remaining_secs() > 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()

                    global _current_bid
                    global _latest_bidder
                    global _remaining_secs

                    # Used to check if current bid has changed
                    prev_bid = _current_bid

                    _remaining_secs = SITE.get_remaining_secs()
                    _current_bid = SITE.get_current_bid()
                    _latest_bidder = SITE.get_latest_bidder()

                    if prev_bid != _current_bid and _current_bid != 0 and prev_bid is not None:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        log("User '%s' just raised the bid to '%s' on %s seconds left."
                            % (_latest_bidder, _current_bid, _remaining_secs))

                    if _remaining_secs < 6 and _current_bid < max_price:
                        we_won = brute_force_bid(SITE, max_price)
                        if we_won:
                            log("Exiting!")
                            browser.quit()
                            sys.exit(0)

                    time.sleep(0.5)

                else:
                    # The auction seems to be ended
                    time.sleep(5)
                    _current_bid = SITE.get_current_bid()
                    _latest_bidder = SITE.get_latest_bidder()
                    log("Auction has ended, winning bid is '%s' by '%s'." % (_current_bid, _latest_bidder))
                    save_winning_bid_and_log_history(bid=_current_bid, bidder=_latest_bidder)

                    browser.quit()
                    scheduler.enter(5, 1, begin, (url,))

        elif SITE.get_remaining_secs() is None:
            log('Auction seems to be closed. Scheduling restart in 60 secs.')
            scheduler.enter(60, 1, begin, (url,))

        else:
            log('This should not happen.')

    except WebDriverException as e:
        log("Caught WebDriverException, the browser probably crashed. Forcing browser quit and rescheduling restart in 10 seconds.")
        log("The exception was: '%s'" % e)
        traceback.print_exc()
        try:
            SITE.browser.quit()
        except: pass
        scheduler.enter(15, 1, begin, (url,))

    except Exception as e:
        log("Caught unexpected exception: '%s'. Forcing browser quit and rescheduling restart in 60 seconds." % e.message)
        log("The exception was: '%s'" % e)
        traceback.print_exc()

        try:
            SITE.browser.quit()
        except: pass
        scheduler.enter(60, 1, begin, (url,))

def _get_winning_bids(auction_id):
    CURSOR.execute("select datetime, name, amount from winningbid where auction = %s;" % auction_id)
    result = CURSOR.fetchall()
    winning_bids = {}
    for r in result:
        winning_bids[r[0]] = {r[1]: r[2]}

    return winning_bids

def save_winning_bid_and_log_history(bid, bidder):
    timestring = int(time.time())
    CURSOR.execute("insert into winningbid values (%s, %s, '%s', %s);"
                   % (AUCTION_ID, timestring, bidder, bid))
    DBCONN.commit()

    winning_bids = _get_winning_bids(AUCTION_ID)

    history = pprint.pformat(winning_bids)
    log(history)

def brute_force_bid(site, max_price):
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

    _current_bid = None
    while site.get_remaining_secs() > 0:
        __current_bid_last_time = _current_bid
        _current_bid = site.get_current_bid()

        if _current_bid != __current_bid_last_time:
            _latest_bidder = site.get_latest_bidder()
            _remaining_secs = site.get_remaining_secs()
            log("User '%s' just raised the bid to '%s' on %s seconds left."
                % (_latest_bidder, _current_bid, _remaining_secs))

        if _current_bid > my_last_bid and _current_bid < max_price:
                my_last_bid = _current_bid+1
                if my_last_bid <= max_price:
                    log("Placing bid of %s" % my_last_bid)
                    site.do_place_bid(my_last_bid)
                else:
                    log("Current bid is higher than or equal to my max price")
                    return False

        time.sleep(0.1)

    # We assume that we have won! But
    # Let's check if we have lost

    # Wait a few seconds
    log("Checking if we lost")
    time.sleep(3)
    winning_bidder = site.get_latest_bidder()
    last_bid = site.get_current_bid()

    log("Winning bidder: '%s'" % winning_bidder)
    log("Winning bid: '%s'" % last_bid)

    # Double confirm that we have lost, cause it means that we will begin bidding again.
    if winning_bidder != MY_NAME and last_bid != my_last_bid:
        # Too bad, it sure looks like we lost
        log("Too bad, we lost")
        return False

    # Wait... we have won!
    log("I's possible that we've won.")
    return True


if __name__ == '__main__':
    URL = sys.argv[1]
    max_price = int(sys.argv[2])
    USE_BROWSER = sys.argv[3]
    ACTION = sys.argv[4]
    # used for checking if bid has changed
    _current_bid = None


    DBCONN = sqlite3.connect('veilingbot.db')
    CURSOR = DBCONN.cursor()
    CURSOR.execute("create table if not exists auction ("
                   "id integer primary key autoincrement not null, "
                   "url text);")
    CURSOR.execute("create table if not exists winningbid ("
                   "auction integer, "
                   "datetime integer, "
                   "name text, "
                   "amount integer, "
#                   "winning integer, "
                   "foreign key(auction) references auctions(id));")

    CURSOR.execute("select id from auction where url = '%s'" % URL)
    result = CURSOR.fetchone()
    if not result:
        CURSOR.execute("insert into auction values (NULL, '%s');" % URL)
        DBCONN.commit()
        CURSOR.execute("select id from auction where url = '%s'" % URL)
        result = CURSOR.fetchone()

    AUCTION_ID = result[0]

    winning_bids = _get_winning_bids(AUCTION_ID)

    scheduler.enter(0, 1, begin, (URL,))

    log('Starting scheduler')
    scheduler.run()
    log('Scheduler finished')
