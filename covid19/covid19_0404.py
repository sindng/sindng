# -*- coding: utf-8 -*-

from __future__ import with_statement
import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from contextlib import closing
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, Markup, Response
from werkzeug.security import check_password_hash, generate_password_hash
import json
from functools import wraps

import calendar
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Table, Column, Float, Integer, String, MetaData, ForeignKey, Date
import requests
from bs4 import BeautifulSoup
import lxml
import re
import yaml
import exception

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


@app.route('/') 
def home(): 
    response = requests.get('https://www.worldometers.info/coronavirus/') 
    soup = BeautifulSoup(response.text, "lxml")
    
    main_cases = get_cases(soup)
    
    graph_values  = get_graph_values(soup)
   
    country_infos = get_country_infos(soup)
    
    return render_template('parse.html', country_infos=country_infos, main_cases=main_cases, graph_values=graph_values) 


def get_graph_values(soup):
    scripts = soup.find_all('script', {'type' : 'text/javascript'})
    patterncases = re.compile(r"coronavirus-cases-linear\'(.*?)\);", re.MULTILINE | re.DOTALL | re.UNICODE)
    patterndeath = re.compile(r"coronavirus-deaths-linear\'(.*?)\);", re.MULTILINE | re.DOTALL | re.UNICODE)
    
    cases_linear = str(scripts[10]).replace(' ', '')
    cases_linear_txt = patterncases.findall(cases_linear)
    death_linear = str(scripts[11]).replace(' ', '')
    death_linear_txt = patterndeath.findall(death_linear)

    #==================================================================================================
    pattern = re.compile(r'xAxis:\{(.*?)yAxis', re.MULTILINE | re.DOTALL | re.UNICODE)
    category = pattern.findall(str(cases_linear_txt))

    jsonstr = str(category).strip("'<>(), ").replace('\n', '').replace('\\', '').replace('},nn', '').replace('[\'', '').replace('\']', '').replace('ncategories', '{\"catogories\"') + '}'
    jsonload = json.loads(jsonstr)
    
    xcases = jsonload['catogories']
    #==================================================================================================  
    pattern = re.compile(r'series:.*lineWidth:.*\[(.*?)responsive:', re.MULTILINE | re.DOTALL | re.UNICODE)
    data = pattern.findall(str(cases_linear_txt))

    jsonstr = str(data).replace('[\'', '').replace('\']', '').replace('\\','')
    jsonstr = jsonstr.replace(jsonstr[len(jsonstr)-6 : len(jsonstr)], '')
    jsonstr = '{\"data\": ' + '[' + jsonstr + ']}' 
    
    jsonload = json.loads(jsonstr)
    ycases = jsonload['data']
    #==================================================================================================
    pattern = re.compile(r'xAxis:\{(.*?)yAxis', re.MULTILINE | re.DOTALL | re.UNICODE)
    category = pattern.findall(str(death_linear_txt))

    jsonstr = str(category).strip("'<>(), ").replace('\n', '').replace('\\', '').replace('},nn', '').replace('[\'', '').replace('\']', '').replace('ncategories', '{\"catogories\"') + '}'
    jsonload = json.loads(jsonstr)
    
    xdeaths = jsonload['catogories']
    #==================================================================================================  
    pattern = re.compile(r'series:.*lineWidth:.*\[(.*?)responsive:', re.MULTILINE | re.DOTALL | re.UNICODE)
    data = pattern.findall(str(death_linear_txt))

    jsonstr = str(data).replace('[\'', '').replace('\']', '').replace('\\','')
    jsonstr = jsonstr.replace(jsonstr[len(jsonstr)-6 : len(jsonstr)], '')
    jsonstr = '{\"data\": ' + '[' + jsonstr + ']}' 
    
    jsonload = json.loads(jsonstr)
    ydeaths = jsonload['data']
    #==================================================================================================    
    
    xvalues = []
    xvalues.append(xcases)
    xvalues.append(xdeaths)
    yvalues = []
    yvalues.append(ycases)
    yvalues.append(ydeaths)
    
    graph_values = []
    graph_values.append(xvalues)
    graph_values.append(yvalues)
    
    return graph_values


def get_cases(soup):
    mains = soup.find_all('div', {'class' : 'maincounter-number'})

    cases = mains[0].text
    death = mains[1].text
    recovered = mains[2].text

    main_cases = []
    main_cases.append(cases);
    main_cases.append(death);
    main_cases.append(recovered);

    return main_cases
    

def get_country_infos(soup): 
    table = soup.find('table')
    trs = table.find_all('tr')

    country_infos = []

    for tr in trs[1:] :
        tds = tr.find_all('td')
        if len(tds) > 0:
            country_info = {
                'country' : tds[0].text,
                'totalcases' : tds[1].text,
                'newcases' : tds[2].text,
                'totaldeath' : tds[3].text,
                'newdeath' : tds[4].text,
                'totalrecovered' : tds[5].text,
                'activecases' : tds[6].text
            }
        country_infos.append(country_info)

    return country_infos
    

@app.route('/parse')
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
    app.run(host='61.254.114.230', port=5000)
