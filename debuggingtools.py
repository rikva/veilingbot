from selenium import webdriver
import vakantieveilingen
import ticketveiling
browser = webdriver.Firefox()
vv = vakantieveilingen.VakantieVeilingen(browser, 5, "bid")
tv = tv = ticketveiling.TicketVeiling(browser, 5, 'bid')
print "vars: browser, vv, tv"

