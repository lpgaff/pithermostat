#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Liam Gaffney
"""
import sys
import init
import mymail
import logging
from influxdb import InfluxDBClient

# create logger
lgr = logging.getLogger(__name__)

# InfluxDB Client
client = InfluxDBClient( host=init.INFLUX_HOST, port=init.INFLUX_PORT, database=init.INFLUX_DB, username=init.INFLUX_USER, password=init.INFLUX_PASSWD )

# Send logs
def sendlog( msg, severity="info" ):
	try:
		influx_log = 'syslog,appname=\"' + str(init.APP_NAME) + '\",severity=\"' + str(severity) + '\" message=\"' + str(msg) + '\"'
		r = client.write_points(influx_log,protocol='line')
		return r
	except Exception as e:
		lgr.error("Could not send log to Influx: " + str(e))
		mymail.connectAndSend(retries = 0, sleepTime = 60, emailSubject = "[RPi Thermostat] Could not send log to Influx", emailText=str(e))
		sys.exit("Could not send log to Influx: " + str(e))
		return None
	return None

# Send data
def senddata( payload ):
	try:
		r = client.write_points(payload,protocol='line')
		return r
	except Exception as e:
		lgr.error("Could not send data to Influx: " + str(e))
		mymail.connectAndSend(retries = 0, sleepTime = 60, emailSubject = "[RPi Thermostat] Could not send data to Influx", emailText=str(e))
		sys.exit("Could not send data to Influx: " + str(e))
		return None
	return None



