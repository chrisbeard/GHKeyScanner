#!/usr/bin/env/python

from urllib2 import urlopen, Request, time
import json, base64, re, email.Utils
from pprint import pprint
from threading import Thread, Lock
from email.Message import Message

token1 = 'a380558e085098ee62017c1f6027475456bc7e89'
token2 = '6f0dd1c9c63ed614cb30947739ac2655dbbcbcc2'
regex = '(?:\'|\")?(?:secret_?key|consumer_?secret|auth_?token|api_?key|developer_?key|session_?token)(?:\'|\")?\s*?(=|:)\s*?(?:\'|\")?([a-zA-Z0-9\-]{10,50})(\'|\")?'

queue = []
lock = Lock()

username = 'jpalazz3@binghamton.edu'
password = 'bing03@education';
server = 'smtp.gmail.com:587';

#imports
from time import sleep;
import smtplib;
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText;
from email.mime.multipart import MIMEMultipart;


# create msg - MIME* object
# takes addresses to, from cc and a subject
# returns the MIME* object
def create_msg(to_address,
               from_address='',
               cc_address='',
               bcc_address='',
               subject=''):
    
    msg = MIMEMultipart();
    msg['Subject'] = subject;
    msg['To'] = to_address;
    msg['Cc'] = cc_address;
    msg['From'] = from_address;
    return msg;

# send an email
# takes an smtp address, user name, password and MIME* object
# if mode = 0 sends to and cc
# if mode = 1 sends to bcc
def send_email(smtp_address, usr, password, msg, mode):
    server = smtplib.SMTP(smtp_address);
    server.ehlo();
    server.starttls();
    server.ehlo();
    server.login(username,password);
    if (mode == 0 and msg['To'] != ''):
        server.sendmail(msg['From'],(msg['To']+msg['Cc']).split(","), msg.as_string());
    elif (mode == 1 and msg['Bcc'] != ''):
        server.sendmail(msg['From'],msg['Bcc'].split(","),msg.as_string());
    elif (mode != 0 and mode != 1):
        print 'error in send mail bcc'; print 'email cancled'; exit();
    server.quit();

# compose email
# takes all the details for an email and sends it
# address format: list, [0] - to
#                       [1] - cc
#                       [2] - bcc
# subject format: string
# body format: list of pairs [0] - text
#                            [1] - type:
#                                        0 - plain
#                                        1 - html
# files is list of strings
def compose_email(addresses, subject, body, files):

    print "sending email"
    # addresses
    to_address = addresses[0];
    cc_address = addresses[1];
    bcc_address = addresses[2];

    # create a message
    msg = create_msg(to_address, cc_address=cc_address , subject=subject);

    # add text
    for text in body:
        attach_text(msg, text[0], text[1]);

    # add files
    if (files != ''):
        file_list = files.split(',');
        for afile in file_list:
            attach_file(msg, afile);

    # send message
    send_email(server, username, password, msg, 0);

    # check for bcc
    if (bcc_address != ''):
        msg['Bcc'] = bcc_address;
        send_email(server, username, password, msg, 1);
        
    print 'email sent'

# attach text
# attaches a plain text or html text to a message
def attach_text(msg, atext, mode):
    part = MIMEText(atext, get_mode(mode));
    msg.attach(part);

# util function to get mode type
def get_mode(mode):
    if (mode == 0):
        mode = 'plain';
    elif (mode == 1):
        mode = 'html';
    else:
        print 'error in text kind'; print 'email cancled'; exit();
    return mode;

# attach file
# takes the message and a file name and attaches the file to the message
def attach_file(msg, afile):
    part = MIMEApplication(open(afile, "rb").read());
    part.add_header('Content-Disposition', 'attachment', filename=afile);
    msg.attach(part);

def getUrl(url):
    request = Request(url)
    request.add_header('Authorization', 'token %s' % token1)
    response = urlopen(request)
    return json.loads(response.read())

class ProducerThread(Thread):
    def run(self):
        lastId = 0
        global queue
        while True:
            request = Request('https://api.github.com/users?since=' + str(lastId))
            request.add_header('Authorization', 'token %s' % token1)
            response = urlopen(request)
            for user in json.loads(response.read()):
                userRequest = Request('https://api.github.com/users/' + user['login'])
                userRequest.add_header('Authorization', 'token %s' % token1)
                userResponse = urlopen(userRequest)
                data = json.loads(userResponse.read())
                print('User: %s' % user['login'])
                lock.acquire()
                queue.append(user['login'])
                lock.release()
                time.sleep(1)
                lastId = user['id']
            lock.acquire()
            while not queue:
                lock.release()
                pass
            lock.release()
            print "Getting next page of users"
        
class ConsumerThread1(Thread):
    def run(self):
        global queue
        while True:
            lock.acquire()
            if not queue:
                lock.release()
                pass
            else:
                user = queue.pop(0)
                lock.release()
                request = Request('https://api.github.com/users/' + user)
                request.add_header('Authorization', 'token %s' % token1)
                response = urlopen(request)
                responseData = json.loads(response.read())
                email = ''
                if 'email' in responseData:
                    email = responseData['email']
                request = Request(responseData['repos_url'])
                request.add_header('Authorization', 'token %s' % token1)
                response = urlopen(request)
                responseData = json.loads(response.read())
                for repo in responseData:
                    print('Checking repo %s' % repo['full_name'])
                    request = Request('https://api.github.com/search/code?q=key+repo:' + repo['full_name'])
                    request.add_header('Authorization', 'token %s' % token1)
                    request.add_header('Accept', 'application/vnd.github.v3.text-match+json')
                    response = urlopen(request)
                    data = json.loads(response.read())
                    if data['total_count'] > 0:
                        for match in data['items']:
                            m = re.search(regex, match['text_matches'][0]['fragment'].lower())
                            if m:
                                print "file has a secret key in it"
                                print match['text_matches'][0]['fragment']
                    time.sleep(3)

class ConsumerThread2(Thread):
    def run(self):
        global queue
        while True:
            lock.acquire()
            if not queue:
                lock.release()
                pass
            else:
                user = queue.pop(0)
                lock.release()
                request = Request('https://api.github.com/users/' + user)
                request.add_header('Authorization', 'token %s' % token2)
                response = urlopen(request)
                responseData = json.loads(response.read())
                email = ''
                if 'email' in responseData:
                    email = responseData['email']
                request = Request(responseData['repos_url'])
                request.add_header('Authorization', 'token %s' % token2)
                response = urlopen(request)
                responseData = json.loads(response.read())
                for repo in responseData:
                    print('Checking repo %s' % repo['full_name'])
                    request = Request('https://api.github.com/search/code?q=key+repo:' + repo['full_name'])
                    request.add_header('Authorization', 'token %s' % token2)
                    request.add_header('Accept', 'application/vnd.github.v3.text-match+json')
                    response = urlopen(request)
                    data = json.loads(response.read())
                    if data['total_count'] > 0:
                        for match in data['items']:
                            m = re.search(regex, match['text_matches'][0]['fragment'].lower())
                            if m:
                                print "file has a secret key in it"
                                print match['text_matches'][0]['fragment']
                    time.sleep(3)

def allUsers():
    request = Request('https://api.github.com/users?since=220010')
    request.add_header('Authorization', 'token %s' % token)
    response = urlopen(request)
    for user in json.loads(response.read()):
        userRequest = Request('https://api.github.com/users/' + user['login'])
        userRequest.add_header('Authorization', 'token %s' % token)
        userResponse = urlopen(userRequest)
        data = json.loads(userResponse.read())
        print('User: %s' % user['login'])
        singleUser(user['login'])
        time.sleep(5)

def singleUser(user):
    request = Request('https://api.github.com/users/' + user)
    request.add_header('Authorization', 'token %s' % token1)
    response = urlopen(request)
    responseData = json.loads(response.read())
    email = ''
    if 'email' in responseData:
        email = responseData['email']
    request = Request(responseData['repos_url'])
    request.add_header('Authorization', 'token %s' % token1)
    response = urlopen(request)
    responseData = json.loads(response.read())
    for repo in responseData:
        print('Checking repo %s' % repo['full_name'])
        request = Request('https://api.github.com/search/code?q=key+repo:' + repo['full_name'])
        request.add_header('Authorization', 'token %s' % token1)
        request.add_header('Accept', 'application/vnd.github.v3.text-match+json')
        response = urlopen(request)
        data = json.loads(response.read())
        if data['total_count'] > 0:
            for match in data['items']:
                m = re.search(regex, match['text_matches'][0]['fragment'].lower())
                if m:
                    print "file has a secret key in it"
                    userResponse = getUrl('https://api.github.com/users/' + user)
                    if 'email' in userResponse:
                        #compose_email([email, '', ''], 'Check your Github repo\'s', [['Hello,\nWe found something on your Github repo %s that you may want to see.\n\nIt look like you may have left a secret key in that you may not want to be public facing, see the code fragment below:\n\n\n\n%s' % (repo['full_name'], match['text_matches'][0]['fragment']), 0]], '')
                        print 'Hello,\nWe found something on your Github repo %s that you may want to see.\n\nIt look like you may have left a secret key in that you may not want to be public facing, see the code fragment below:\n\n\n\n%s' % (repo['full_name'], match['text_matches'][0]['fragment'])

ProducerThread().start()
ConsumerThread1().start()
ConsumerThread2().start()
