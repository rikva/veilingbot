import traceback
import time
from selenium.common.exceptions import ElementNotVisibleException, NoSuchElementException
from credentials import USERNAME, PASSWORD
from veilingbotcore import log, make_screenshot, ravenclient, click_element_when_available

class VakantieVeilingen():
    def __init__(self,
                 browser,
                 max_price,
                 action="dryrun"):
        self.browser = browser
        self.action = action
        self.max_price = max_price

    def get_remaining_secs(self):
        seconds_left = ''
        while not seconds_left.isdigit():
            try:

                # it can take a few moments for the auction time to dynamically load. Before that, it's empty
                auction_time = ""
                while auction_time == "":
                    auction_time = self.browser.find_element_by_class_name('auction-time').text.lower()

                hours = 0
                mins = 0

                if not 'sec' in auction_time:
                    log('Auction has probably ended. Time string was: "%s"' % auction_time)
                    make_screenshot(self.browser)
                    return 0

                if 'uur' in auction_time:
                    hours, _, auction_time = auction_time.partition("uur")

                if 'min' in auction_time:
                    mins, _, auction_time = auction_time.partition("min")

                secs, _, auction_time = auction_time.partition("sec")

                seconds_left = int(secs)
                seconds_left += (int(mins) * 60)
                seconds_left += ((int(hours) * 60) * 60)
                return seconds_left

            except Exception as e:

                log("EXCEPTION ! DEBUG: '%s'" % e)
                log('Returning 11 seconds')
                traceback.print_exc()
                ravenclient.captureException()
                return 11

    #            raise


    def get_current_bid(self):
        price = self.browser.find_element_by_xpath("//span[@ng-model='auction.price.amount']")
        if price.is_displayed():
            return int(price.text)


    def get_latest_bidder(self):
        try:
            first_name = self.browser.find_elements_by_xpath('//span[@ng-bind="bid.customer.firstName"]')[0].text
            prefix = self.browser.find_elements_by_xpath('//span[@ng-bind="bid.customer.lastNamePrefix"]')[0].text
            last_name = self.browser.find_elements_by_xpath('//span[@ng-bind="bid.customer.lastName"]')[0].text
            if prefix:
                return "%s %s %s" % (first_name, prefix, last_name)
            return "%s %s" % (first_name, last_name)

        except:
            ravenclient.captureException()
            return 'unknown'

    def _is_logged_in(self):
        if self.browser.find_elements_by_link_text("Uitloggen"):
            return True
        return False

    def do_login(self):
        if self._is_logged_in():
            log ("Already signed in")
            return True

        log('Signing in')
        click_element_when_available(self.browser.find_element_by_link_text, "Inloggen")
        time.sleep(1)

        email = [f for f in self.browser.find_elements_by_xpath("//input[@ng-model='email']") if f.is_displayed()][0]
        passwd = [f for f in self.browser.find_elements_by_xpath("//input[@ng-model='password']") if f.is_displayed()][0]
        button = [f for f in self.browser.find_elements_by_xpath("//input[@value='Login']") if f.is_displayed()][0]

        email.send_keys(USERNAME)
        passwd.send_keys(PASSWORD)
        button.click()

        counter = 0
        log('Waiting max. 10 seconds')
        while not self._is_logged_in():
            time.sleep(1)
            counter += 1
            log(counter)
            if counter > 10:
                log('Login failed.')
                make_screenshot(self.browser)
                return False
        else:
            log('Logged in successfully.')
            return True

    def do_place_bid(self, price):
        log("ACTION is %s" % self.action)
        if self.action != "bid":
            log("We are doing a dry run. Not bidding!")
            return

        if int(price) > int(self.max_price):
            log("FAILSAFE (this should not happen): not placing bid of %s, it's higher than %s" %
                (price, self.max_price))
        else:
            log("Placing bid of '%s' euro" % price )
            ub = self.browser.find_element_by_xpath("//input[@name='bidAmount']")
            # first clear the input field!
            log('DEBUG: Clearing input field')
            ub.clear()
            log('DEBUG: Sending %s to input field' % price)
            ub.send_keys(price)
            click_element_when_available(self.browser.find_element_by_link_text, "Bied mee!")

            time.sleep(0.2)
            try:
                self.browser.find_element_by_link_text("Plaats bod").click()
            except (ElementNotVisibleException, NoSuchElementException):
                # This can happen when auto-confirm is checked.
                log("Could not confirm, this is probably OK.")
            log('Placed bid for %s EUR' % price)
            time.sleep(0.2)
            # Try to close all dialogs:
            log('DEBUG: Closing any dialogs')
            for dialog in self.browser.find_elements_by_class_name('DialogClose'):
                log("Encountered dialog with text: '%s'" % dialog.text)
                try:
                    dialog.click()
                    log('Closed a dialog window.')
                except ElementNotVisibleException:
                    log("Could not close invisible dialog")
                except:
                    log('Failed to close a dialog.')
