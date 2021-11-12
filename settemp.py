#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Liam Gaffney
"""
import init
import mymail
import logging 

def do_settemp(temp):
	lgr = logging.getLogger(__name__)
	lgr.info("Setting temperature invoked with the following arguments " + str(temp))
	if temp:
		try:
			float(temp)
			lgr.debug("Temperature seems to be a correct float value")
			f = open(init.T_FILE, "w")
			lgr.debug("File successfully open")
			f.write("T = " + str(temp))
			lgr.debug("Temp written")
			f.close()
		except Exception as e:
			lgr.error("Could not write temperature " + str(temp) + ", error: " + str(e))
			mymail.connectAndSend(retries = 0, sleepTime = 60, emailSubject = "[RPi Thermostat] Could not write temperature " + temp, emailText=str(e))
			sys.exit("Could not write temperature " + str(temp) + ", error: " + str(e))

