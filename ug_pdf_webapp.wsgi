#! /usr/bin/python3.6

import logging
import sys
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/var/www/ug-pdf')

from ug_pdf_webapp import app as application
application.secret_key = 'anything you wish'
