import traceback
import time
from selenium.common.exceptions import ElementNotVisibleException
from credentials import USERNAME, PASSWORD
from veilingbotcore import log, make_screenshot, go_to_url


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
                counter_span = self.browser.find_element_by_class_name('counter-running')
                celement = counter_span.find_element_by_tag_name('span')
                timestring = celement.text.split()

                if timestring[0] == 'Gesloten' or timestring[0] == '':
                    log('Auction has ended.')

                    make_screenshot(self.browser)

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

                log("EXCEPTION ! DEBUG: '%s'" % e)
                log('Returning 11 seconds')
                traceback.print_exc()
                return 11

    #            raise


    def get_current_bid(self):
        for i in range(10):
            try:
                for price in self.browser.find_elements_by_class_name('price'):
                    if price.text:
                        if len(price.text.split()) == 2:
                            return int(price.text.split()[1])
                        log("Woah wait this should not happen")
                        break
            except Exception as e:
                log("DEBUG: Could not obtain price. Exception: %s.Printing traceback." % e)
                traceback.print_exc()

    def get_latest_bidder(self):
        try:
            bh = self.browser.find_element_by_id('biddinghistory')
            li = bh.find_element_by_tag_name('li')
            p = li.find_element_by_tag_name('p')
            st = p.find_element_by_tag_name('strong')
            return st.text
        except:
            return 'unknown'


    def do_login(self, return_url=None):
        log('Signing in')
        time.sleep(2)
        go_to_url(self.browser, "https://www.vakantieveilingen.nl/login.html")
        log('Waiting 2 secs')
        time.sleep(2)

        open_login = self.browser.find_element_by_class_name('openLogin')
        open_login.click()

        email = self.browser.find_element_by_id('loginEmailField')
        passwd = self.browser.find_element_by_id('loginPasswordField')

        form = self.browser.find_element_by_id('LoginForm')
        fieldset = form.find_element_by_tag_name('fieldset')
        button = fieldset.find_elements_by_tag_name('input')[-1]

        email.send_keys(USERNAME)
        passwd.send_keys(PASSWORD)
        button.click()

        counter = 0
        log('Waiting max. 30 seconds')
        while not self.browser.current_url.startswith("https://www.vakantieveilingen.nl/myauctions"):
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
                go_to_url(self.browser, return_url)
                log("Current bid is: %s" % self.get_current_bid())
            return True

    def do_place_bid(self, price):
        log("ACTION is %s" % self.action)
        if self.action != "bid":
            log("We are doing a dry run. Not bidding!")
            make_screenshot(self.browser)
            return

        if int(price) > int(self.max_price):
            log("FAILSAFE (this should not happen): not placing bid of %s, it's higher than %s" %
                (price, self.max_price))
        else:
            log("Placing bid of '%s' euro" % price )
            ub = self.browser.find_element_by_id('userBid')
            # first clear the input field!
            log('DEBUG: Clearing input field')
            ub.clear()
            log('DEBUG: Sending %s to input field' % price)
            ub.send_keys(price)
            bm = self.browser.find_element_by_id('PrototypeLoginTrigger')
            # The "Bid" button
            log('DEBUG: clicking PrototypeLoginTrigger button')
            bm.click()
            time.sleep(0.2)
            try:
                pb = self.browser.find_element_by_id('placeBidButton')
                # The "Confirm" button
                log('DEBUG: Clicking placeBidButton')
                pb.click()
            except ElementNotVisibleException:
                # This can happen when auto-confirm is checked.
                log("Could not confirm, this is propably OK.")
            log('Placed bid for %s EUR' % price)
            time.sleep(0.2)
            # Try to close all dialogs:
            log('DEBUG: Closing any dialogs')
            for dialog in self.browser.find_elements_by_class_name('DialogClose'):
                try:
                    dialog.click()
                    log('Closed a dialog window.')
                except ElementNotVisibleException:
                    log("Could not close invisible dialog")
                except:
                    log('Failed to close a dialog.')
