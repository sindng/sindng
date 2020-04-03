# -*- coding: utf-8 -*-

from __future__ import with_statement
import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from contextlib import closing
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, Markup
from werkzeug.security import check_password_hash, generate_password_hash


import calendar
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Table, Column, Float, Integer, String, MetaData, ForeignKey, Date
from flask import request
from bs4 import BeautifulSoup


app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('MINITWIT_SETTINGS', silent=True)
app.config['SECRET_KEY'] = 'this is secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



labels = [
    'JAN', 'FEB', 'MAR', 'APR',
    'MAY', 'JUN', 'JUL', 'AUG',
    'SEP', 'OCT', 'NOV', 'DEC'
]

values = [
    967.67, 1190.89, 1079.75, 1349.19,
    2328.91, 2504.28, 2873.83, 4764.87,
    4349.29, 6458.30, 9907, 16297
]

colors = [
    "#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA",
    "#ABCDEF", "#DDDDDD", "#ABCABC", "#4169E1",
    "#C71585", "#FF4500", "#FEDCBA", "#46BFBD"]

@app.route('/parse')
def parse():
    req = requests.get('https://www.daum.net/')
    
    

@app.route('/')
def mainlist():
    f = open('static/countries.txt', 'r')
 #   return "</br>".join()
    return render_template('main2.html', country_names=f.readlines(), curtime=int(time.time()))

@app.route('/country/<country_name>')
def country_status(country_name=None):
    if not country_name:
        return redirect(url_for('mainlist'))
    
    line_labels = labels
    line_values = values
    return render_template('chart.html', title='Covid-19 '+country_name, country_name=country_name, max=20000, labels=line_labels, values=line_values)

def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @')
    #return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')

def gravatar_url(email, size=40):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), 
         size)
        

# add some filters to jinja
app.jinja_env.filters['gravatar'] = gravatar_url
app.jinja_env.filters['datetimeformat'] = format_datetime
#app.jinja_env.filters['chartfilter'] = chart

if __name__ == '__main__':
    app.run(host='61.254.114.230', port=5001)