#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Liam Gaffney
""" 
# smtplib module send mail
import smtplib
# imaplib module sends mail
import imaplib
import init
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import time

# create logger
lgr = logging.getLogger(__name__)

def serverConnect(account, password, server, port=587):
	lgr.debug("serverConnect invoked. Parameters: " + str(locals()))
	lgr.debug("Params. Account: " + account + ", password: " + password + ", server: " + server + ", port: " + str(port))
	if int(port) == 465:	# gmail server
		lgr.debug("smtplib.SMTP_SSL - Connecting to ssl gmail smtp port 465")
		email_server = smtplib.SMTP_SSL(server, str(port))
		email_server.login(account, password)
	else:
		lgr.debug("smtplib.SMTP - Connecting to non ssl smtp port: " + port)
		email_server = smtplib.SMTP(server, str(port))
		lgr.debug("Invokining ehlo")
		email_server.ehlo()
		lgr.debug("Invoking starttls")
		email_server.starttls()
		lgr.debug("Invoking login")
		email_server.login(account, password)
		lgr.debug("Login successful - returning")
	return email_server

def readEmail(account=init.GMAIL_SENDER, password=init.GMAIL_PASSWD, server=init.GMAIL_READER):

	# Login to Gmail
	lgr.debug("readEmail invoked. Parameters: " + str(locals()))
	email_reader = imaplib.IMAP4_SSL(server)
	email_reader.login(account, password)
	email_reader.select('inbox')
	email_reader.list()
	typ, data = email_reader.search(None, 'ALL')
	for num in data[0].split():
		typ, data = email_reader.fetch(num, '(RFC822)')
	typ, data = email_reader.search(None, 'ALL')
	ids = data[0] # data is a list
	id_list = ids.split() # ids is a space separated string
	total_emails = len(id_list)

	lgr.debug("Found " + str(total_emails) + " new emails")

	new_temp = -666
	goodmail = 0

	# get most recent email id
	if id_list:
		latest_email_id = int(id_list[-1]) # this is the latest id
		for i in range( latest_email_id, latest_email_id - total_emails, -1 ):
			typ, data = email_reader.fetch( str(i), '(RFC822)')
			for response_part in data:
				if isinstance(response_part, tuple):
					msg = email.message_from_bytes(response_part[1])
					varSubject = msg['subject']
					varFrom = msg['from']
					varFrom = varFrom.replace('<', '')
					varFrom = varFrom.replace('>', '')
					lgr.debug("Email with ID: " + str(i) + " from: " + str(varFrom) + " with subject: " + str(varSubject))

			if ( ( len(varFrom.rsplit(" ",1)) < 2 ) and (varFrom == account) ):
				goodmail = 1
			elif ( varFrom.rsplit(" ",1)[1] == account ):
				goodmail = 1
			else:
				goodmail = 0

			if goodmail == 1:
				if len(varSubject) > 0:
					if varSubject[0] == '[':
						varSubject = varSubject.replace('[','')
						varSubject = varSubject.replace(']','')
					try:
						new_temp = float(varSubject)
						msg = "Found a new temperature setting in emails: " + str(new_temp)
						lgr.info(msg)
						break
					except Exception as e:
						lgr.debug("Email not in the correct format")
				else:
					lgr.debug("Email not in the correct format")

	else:
		lgr.debug("Failed to get the list of email IDs")


	# Remove used emails from mailbox
	typ, data = email_reader.search(None, 'ALL')
	id_list = data[0].split()
	lgr.debug("Cleaning up " + str(len(id_list)) + " old emails")
	for num in id_list:
		email_reader.store(num, '+FLAGS', '\\Deleted')
	email_reader.expunge()
	email_reader.close()
	email_reader.logout()

	return new_temp

def sendEmail(srv, emailTo=init.EMAIL_TO, emailSubject = init.EMAIL_SUBJECT, emailText=init.EMAIL_TEXT, emailFrom=init.GMAIL_SENDER, gmailPasswd = init.GMAIL_PASSWD, gmailPort = init.GMAIL_PORT, gmailServer=init.GMAIL_SERVER):
	lgr.debug("sendEmail invoked. Parameters: " + str(locals()))
	msg = MIMEMultipart()
	msg['From'] = emailTo
	msg['To'] = emailFrom
	msg['Subject'] = emailSubject
	msg.attach(MIMEText(emailText, 'plain'))
	lgr.debug("Invoking sendmail("+ emailFrom + ", " + emailTo + ", " + msg.as_string() + ")")
	srv.sendmail(emailFrom, emailTo, msg.as_string())
	lgr.debug("sendmail successful")
	srv.quit()


# Try to send email once and
def connectAndSendOnce(emailTo=init.EMAIL_TO, emailSubject = init.EMAIL_SUBJECT, emailText=init.EMAIL_TEXT, emailFrom=init.GMAIL_SENDER, gmailPasswd = init.GMAIL_PASSWD, gmailPort = init.GMAIL_PORT, gmailServer=init.GMAIL_SERVER):
	# In this function I will only catch the errors which mean that the whose setup doesn't work - no point in retrying
	try:
		server = serverConnect(emailFrom, gmailPasswd, gmailServer, gmailPort)
		if server:
			msg = sendEmail(server, emailTo, emailSubject, emailText, emailFrom, gmailPasswd, gmailPort, gmailServer)
			return msg
	except (smtplib.SMTPException)  as e:
		lgr.error("SMTPAuthenticationError caught while sending email: " + str(e))
		return None
	return None

# send email, retrying when connection error. Set 0 for infinite retries. Time in seconds
def connectAndSend(retries = 10, sleepTime = 60, emailTo=init.EMAIL_TO, emailSubject = init.EMAIL_SUBJECT, emailText=init.EMAIL_TEXT, emailFrom=init.GMAIL_SENDER, gmailPasswd = init.GMAIL_PASSWD, gmailPort = init.GMAIL_PORT, gmailServer=init.GMAIL_SERVER):
	condition = True
	times = 0
	while(condition):
		times+=1
		if (retries > 0):
			condition = (times<retries)
		try:
			msg = connectAndSendOnce(emailTo, emailSubject, emailText, emailFrom, gmailPasswd, gmailPort, gmailServer)
			return msg
		except OSError as e:
			lgr.warning("Could not connect to SMTP server. Attempt " + str(times) + "/" + str(retries) + " with timeout " + str(sleepTime) + ". OSError: " + str(e))
			time.sleep(sleepTime)
			continue
		except:
			lgr.error("Fatal unknown error while sending email: ")
			return None
	lgr.error("Reached maximum number or retries. Returning None")
	return None
