from utils import *
import logging
import json
#import hashlib
import sys
#import tempfile
import csv
import pysftp
from collections import OrderedDict
#from requests.auth import HTTPBasicAuth
from jinja2 import Template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Setting up some pseudo constants
LOG_LEVEL = logging.INFO if ("DEBUG" not in os.environ) else logging.DEBUG

#logging.basicConfig(format='%(asctime)s - %(message)s', level=LOG_LEVEL)
root = logging.getLogger()
root.setLevel(LOG_LEVEL)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

# send_email sends an email, based on parameters in the params argument:
#   from - the email address to send from
#   to - the email address to send to
#   subject - the subject of the email
#   body - the HTML body to send. 
#
# the config argument is expected to be an output from GetParamInfo(), 
# and must contain sendgrid config parameters in config['sendgrid'] for
# both "api_key" and "from"
def send_email(config, params):

  try:
    # Python 3
    import urllib.request as urllib
  except ImportError:
    # Python 2
    import urllib2 as urllib

  # Ensure the api key is specified, and set up the client
  if "sendgrid" not in config or "api_key" not in config['sendgrid']:
    logging.error("No Sendgrid API Key in Parameters")
    return
  logging.debug("Using APIKEY: %s" % config['sendgrid']['api_key'])
  sg = SendGridAPIClient(config['sendgrid']['api_key'])

  # Preprocess to and cc params
  to_mail = [ (params['to'], params['to']) ]
  if ("cc" in params) and (params['cc'] != params['to']):
    to_mail.append((params['cc'], params['cc']))
  # Create the email
  mail = Mail(from_email=params['from'],
              subject=params['subject'],
              to_emails=to_mail,
              html_content=params['body'])

  # Send it or fail trying...
  try:
    response = sg.send(mail)
    print(response.status_code)
    print(response.body)
  except Exception as e:
    print(e)


# The handler... 
def lambda_handler(event, context):
  # Get the config from the SSM params
  config = getParamInfo()
  template_values(config,config,tokens)
  logging.debug("Config: %s" % json.dumps(config))
  
  # Set up the email templates. 
  subject_template = "TESTING: Content Deleted from Degreed Pathway: {{ record.pathway_title }}"
  body_template = "<P>TESTING, PLEASE IGNORE</P><P>Hi - </P><P>You are receiving this email because you are the creator of the Degreed Pathway: {{ record.pathway_title }}, and one of the lessons in that pathway is a wiki page that has been removed: {{ record.wiki_url }}. Please make any necessary changes to the pathway at your earliest convenience.</P><P>Thanks,<br>The Learning Admins</P>"
 

  
  logging.debug("Event: %s" % json.dumps(event))
  # If we've not gotten a list of dicts, the event is not in the right format.
  logging.info("List Element: %s" % type(event[0]))
  if not isinstance(event, list) or isinstance(event[0], dict):
    logging.error("Event is not a list - incorrect format for processing: %s" % json.dumps(event))
  else:
    for record in event:
      params = {}
      logging.info("Sending email to %s, about pathway %s and url %s" % (record['send_to'],record['pathway_title'],record['wiki_url']))
      
      # set up the to field from the record, and the cc field
      
      params['to'] = "steve.litras@autodesk.com"
      params['cc'] = "des.learning.service.admins@autodesk.com"
      
      # Subject and Body are expected to be jinja2 templates, using data from the record object
      try:
        tpl = Template(subject_template)
      except Exception as e:
        logging.error("Error: %s" % e)
      params['subject'] = tpl.render(record=record)
      
      try:
        tpl = Template(body_template)
      except Exception as e:
        logging.error("Error: %s" % e)
      params['body'] = tpl.render(record=record)
      
      # Set the from address, if specified in the config SSM params
      if "sendgrid" in config and "from" in config['sendgrid']:
        params['from'] = config['sendgrid']['from']
      
      # Send the email...
      send_email(config, params)
