#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Liam Gaffney
"""
import requests
import logging
import pigpio
import DHT22
import RPi.GPIO as GPIO
import init
import sys
import mydb
import mymail
import settemp
import t
import time
from influxdb import InfluxDBClient

HTTP_TIMEOUT=10
dtemp=t.T
xtemp=0
t_low=0
t_high=0
err_flag=False

def toggleHeating():
	try:
		GPIO.output(init.RELAY_BCM, not GPIO.input(init.RELAY_BCM))
	except Exception as e:
		msg = "Could not toggle heating for GPIO " + str(init.RELAY_BCM) + ", error: " + str(e)
		mydb.sendlog(msg,"err")
		lgr.error(msg)
		mymail.connectAndSend(retries = 3, sleepTime = 5, emailSubject = "[RPi Thermostat] Could not toggle heating for GPIO " + str(init.RELAY_BCM), emailText=str(e))
		#sys.exit(msg)

def getHeatingState():
	if (GPIO.input(init.RELAY_BCM) == GPIO.HIGH):
		return False
	elif (GPIO.input(init.RELAY_BCM) == GPIO.LOW):
		return True


# function to trigger and read the sensor
def read_sensor_data(s):

	ntries = 0
	temp = -999.0
	humi = -999.0
	err_count = s.missing_message()
	err_count_prev = int(err_count) - 1

	while( int(err_count_prev) < int(err_count) and int(ntries) < 5 ):

		# Power cycle the sensor if there's an error
		if ntries > 0:
			s.pi.write(init.POWER_BCM, 0)
			time.sleep(3)
			s.pi.write(init.POWER_BCM, 1)
			time.sleep(3)

		# Trigger the readout of the DHT22 sensor
		try:
			lgr.debug("Triggering the sensor")
			s.trigger()
			time.sleep(2.2) # just so the Pi doesn't go too fast
		except Exception as e:
			msg = "Problem triggering the sensor, error:  " + str(e)
			mydb.sendlog(msg,"err")
			lgr.error(msg)
			mymail.connectAndSend(retries = 3, sleepTime = 5, emailSubject = "[RPi Thermostat] Problem triggering the sensor", emailText=str(e))
			#sys.exit(msg)

		# Get Temperature from the DHT22 sensor
		try:
			#lgr.debug("Reading temperature")
			temp = s.temperature()
			#time.sleep(0.5)
			lgr.debug("Temperature: " + str(temp))
		except Exception as e:
			msg = "Could not read temperature: " + str(e)
			mydb.sendlog(msg,"err")
			lgr.error(msg)

		# Get humidity from the DHT22 sensor
		try:
			#lgr.debug("Reading humidity")
			humi = s.humidity()
			#time.sleep(0.5)
			lgr.debug("Humidity: " + str(humi))
		except Exception as e:
			msg = "Could not read humidity: " + str(e)
			mydb.sendlog(msg,"err")
			lgr.error(msg)

		# debug
		msg = str(s.staleness()) + " " + str(s.bad_checksum()) + " " + str(s.short_message()) + " "
		msg += str(s.missing_message()) + " " + str(s.sensor_resets())
		lgr.debug(msg)

		# Try again if we didn't get a good temperature reading
		ntries += 1
		err_count_prev = err_count
		err_count = int(s.missing_message())

	return ( float(temp), float(humi) )


# Check email for new temperature settings
def check_for_updates():

	global xtemp, dtemp, t_low, t_high

	try:
		newT = mymail.readEmail()
		if newT > -50:
			msg = "Setting new temperature from email: " + str(newT)
			mydb.sendlog(msg,"info")
			lgr.info(msg)
			settemp.do_settemp(newT)
			dtemp = newT
		else:
			lgr.debug("Continuing with previous temperature")
			newT = -666

		xtemp = float(newT) # if temperature isn't updated, newT = -666

	except Exception as e:
		msg = "Couldn't read emails, error " + str(e)
		mydb.sendlog(msg,"err")
		lgr.error(msg)
		mymail.connectAndSend(retries = 3, sleepTime = 5, emailSubject = "[RPi Thermostat] Couldn't read emails", emailText=str(e))
		#sys.exit(msg)

	# if TEMP_OveRRIDE is sen in init.py, then it overrides the temp being set by scheduler in t.py
	if (init.TEMP_OVERRIDE !=0):
		xtemp = init.TEMP_OVERRIDE
	elif xtemp < -50: # if we haven't just got a new T from email, newT = -666, use demand temp from t,py
		xtemp = dtemp

	t_low = xtemp - init.TEMP_HYSTERESIS
	t_high = xtemp + init.TEMP_HYSTERESIS



# Logger importing
lgr = logging.getLogger(__name__)

# InfluxDB Client
client = InfluxDBClient( host=init.INFLUX_HOST, port=init.INFLUX_PORT, database=init.INFLUX_DB, username=init.INFLUX_USER, password=init.INFLUX_PASSWD )

# this connects to the pigpio daemon which must be started first
# Pigpio DHT22 module should be in same folder as your program
try:
	lgr.debug("Connecting the pigpio daemon")
	pi = pigpio.pi()
except Exception as e:
	msg = "Couldn't connect to the pigpio daemon, error: " + str(e)
	mydb.sendlog(msg,"err")
	lgr.error(msg)
	mymail.connectAndSend(retries = 5, sleepTime = 5, emailSubject = "[RPi Thermostat] Couldn't connect to the pigpio daemon", emailText=str(e))
	sys.exit(msg)


# Initiate the sensor
try:
	lgr.debug("Getting sensor on pin " + str(init.SENSOR_BCM))
	sensor = DHT22.sensor(pi, init.SENSOR_BCM, power=init.POWER_BCM)
except Exception as e:
	msg = "Could not get sensor with on pin " + str(init.SENSOR_BCM) + ", error: " + str(e)
	mydb.sendlog(msg,"err")
	lgr.error(msg)
	mymail.connectAndSend(retries = 5, sleepTime = 5, emailSubject = "[RPi Thermostat] Could not get sensor on pin " + str(init.SENSOR_BCM), emailText=str(e))
	sys.exit(msg)

# Initiate the relay
try:
	lgr.debug("Setting up GPIO")
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(init.RELAY_BCM,GPIO.OUT)
	lgr.debug("GPIO " + str(init.RELAY_BCM) + " initialized as out. Current state: " + str(GPIO.input(init.RELAY_BCM)))
except Exception as e:
	msg = "Could not set up GPIO, error: " + str(e)
	mydb.sendlog(msg,"err")
	lgr.error(msg)
	mymail.connectAndSend(retries = 3, sleepTime = 5, emailSubject = "[RPi Thermostat] Could not set up GPIO", emailText=str(e))
	sys.exit(msg)


# First check of emails for new temperature settings
check_for_updates()
next_reading = time.time()

# Loop through every minute
while True:

	# Read the sensor data
	temp, humi = read_sensor_data(sensor)

	# Next reading time
	next_reading += init.REP_TIME

	# Log the data with Influx and change the heating
	payload = []
	if ((float(temp) > -50.0) and (float(humi) > -50.0)):

		# Clear the error flag, we have a good measurement
		err_flag = False

		# Test the heating cycle
		payload_b = ''
		if ((not getHeatingState()) and (temp < t_low)):
			msg = "Temperature " + str(temp) + " < " + str(t_low) + ". Turning on"
			lgr.info(msg)
			mydb.sendlog(msg,"info")
			toggleHeating()
			payload_b = 'boilerstate value=1'
		elif ((getHeatingState()) and (temp > t_high)):
			msg = "Temperature " + str(temp) + " > " + str(t_high) + ". Turning off"
			lgr.info(msg)
			mydb.sendlog(msg,"info")
			toggleHeating()
			payload_b = 'boilerstate value=0'
		else:
			if getHeatingState():
				payload_b = 'boilerstate value=1'
			else:
				payload_b = 'boilerstate value=0'
			lgr.debug("Temperature ok. Low: " + str(t_low) + ", current: " + str(temp) + ", high:  " + str(t_high) + ", Heating: " + str(getHeatingState()))


		try:
			lgr.debug("Sending data to Influx")
			payload.append('temperature,sensor=' + str(init.LOCATION) + ' value=' + ('%.3f' % temp) )
			payload.append('humidity,sensor=' + str(init.LOCATION) + ' value=' + ('%.3f' % humi) )
			payload.append('settemp value=' + str(xtemp) )
			payload.append(payload_b)
			r = mydb.senddata(payload)
			lgr.debug("Influx payload: " + str(payload))
			lgr.debug("Influx result: {0}".format(r) )
		except Exception as e:
			lgr.error("Could not send data to Influx: " + str(e))
			mymail.connectAndSend(retries = 0, sleepTime = 60, emailSubject = "[RPi Thermostat] Could not send data to Influx", emailText=str(e))
			#sys.exit("Could not send data to Influx: " + str(e))



	# Bad readings from the probe
	else:

		# Test the heating cycle for ON/OFF values at least (30/0)
		payload_b = ''
		if ((not getHeatingState()) and (xtemp > 29.9)):
			msg = "Set temperature = " + str(xtemp) + " means on, overriding bad readings " + ". Turning on"
			lgr.info(msg)
			mydb.sendlog(msg,"info")
			toggleHeating()
			payload_b = 'boilerstate value=1'
		elif ((getHeatingState()) and (xtemp < 0.1)):
			msg = "Set temperature = " + str(xtemp) + " means off, overriding bad readings " + ". Turning off"
			lgr.info(msg)
			mydb.sendlog(msg,"info")
			toggleHeating()
			payload_b = 'boilerstate value=0'
		elif (not err_flag):
			error_string = "Problem reading the sensor: temp = " + str(temp) + "; humidity = " + str(humi)
			error_string += "\nHeating control in manual mode because of bad temperature readings. Fix me!"
			if getHeatingState():
				error_string += "\nTurning heating off for now to be safe."
				toggleHeating()
				payload_b = 'boilerstate value=0'
			lgr.error(str(error_string))
			mydb.sendlog(error_string,"err")
			mymail.connectAndSend(retries = 0, sleepTime = 60, emailSubject = "[RPi Thermostat] Problem reading the sensor", emailText=str(error_string))
		else:
			if getHeatingState():
				payload_b = 'boilerstate value=1'
			else:
				payload_b = 'boilerstate value=0'

		payload.append('settemp value=' + str(xtemp) )
		payload.append(payload_b)
		r = mydb.senddata(payload)
		lgr.debug("Influx payload: " + str(payload))
		lgr.debug("Influx result: {0}".format(r) )

		# Set error flag so we don't send repeated logs/emails
		err_flag = True

	# Wait for a minute or two
	waiting = float(next_reading-time.time())
	if waiting < 10.0:
		waiting = 10.0
	time.sleep(waiting)

	# Check for the new temperature and start again
	check_for_updates()

s.cancel()
pi.stop()

