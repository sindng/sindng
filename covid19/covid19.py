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


@app.route('/jam')
def jam():
    response = requests.get('http://www.slrclub.com/bbs/zboard.php?id=hot_article&category=1&setsearch=category') 
    soup = BeautifulSoup(response.text, "lxml")
    
    prev_next = get_prevNext(soup) 
    slrlist = get_slrlist(soup)
    
    return render_template('jam.html', slrlist=slrlist, prev_next=prev_next) 


@app.route('/jam/<link>')
def jam_newpage(link=None):
    
    if not link:
         return redirect(url_for('jam'))
     
    print("link prev : {0}".format(link))
    link = link.replace('%3F', '?').replace('%3D', '=').replace('%26', '&')
   
    link = 'http://www.slrclub.com/bbs/' + link
    print("link after : {0}".format(link))
     
    response = requests.get(link) 
    soup = BeautifulSoup(response.text, "lxml")
    
    prev_next = get_prevNext(soup) 
    slrlist = get_slrlist(soup)
    
    return render_template('jam.html', slrlist=slrlist, prev_next=prev_next)

def get_prevNext(soup):
    table = soup.find_all('table', {'id' : 'bbs_foot'})
    btns = table[0].find_all('td', {'class' : 'btn1'})
    
    preva = btns[0].find_all('a', {'class' : 'prev1 bh bt_fpg'})
    nexta = btns[0].find_all('a', {'class' : 'next1 bh bt_npg'})
    patternurl = re.compile(r"href=\"(.*?)\" title=", re.MULTILINE | re.DOTALL | re.UNICODE)

    print(table[0])
    print("btns : {0}".format(btns))
    print("prev url : {0}".format(preva))
    print("next url : {0}".format(nexta))

    urls = []
    
    if preva:
        prev_url = patternurl.findall(str(preva))
        link = str(prev_url).replace('[\'','').replace('\']','').replace('amp;','').replace('/bbs','')
        url = {
            'title' : '<--- prev',
            'link' : link
        }
        urls.append(url)
        print("prev url : {0}".format(link))
    
    if nexta:   
        next_url = patternurl.findall(str(nexta))
        link = str(next_url).replace('[\'','').replace('\']','').replace('amp;','').replace('/bbs','')
        url = {
            'title' : 'next --->',
            'link' : link
        }
        urls.append(url)
        print("next url : {0}".format(link))

    print("urls : {0}".format(urls))
    return urls

def get_slrlist(soup):
    table = soup.find_all('table', {'id' : 'bbs_list'})
    trs = table[0].find_all('tr')  

    patternurl = re.compile(r"a href=\"(.*?)\"", re.MULTILINE | re.DOTALL | re.UNICODE)
    infos = []
    
    for tr in trs[1:] :

        tds = tr.find_all('td')
        td_infos = []
        
        i = 0 
        for td in tds :
            td_infos.append(td.text)
            if i == 2:
                atag = td.find('a')
                url = patternurl.findall(str(atag))
                link = str(url).replace('[\'','').replace('\']','').replace('amp;','')
                td_infos.append(link)
            
            i = i + 1
            
        infos.append(td_infos)

    #print(infos)
    
    return infos

@app.route('/') 
def home(): 
    response = requests.get('https://www.worldometers.info/coronavirus/') 
    soup = BeautifulSoup(response.text, "lxml")
    
    main_cases = get_cases(soup)
    
    graph_values  = get_graph_values(soup)
   
    country_infos = get_country_infos(soup)
    
    return render_template('parse.html', country_infos=country_infos, main_cases=main_cases, xcases=graph_values[0][0], ycases=graph_values[1][0], xdeaths=graph_values[0][1], ydeaths=graph_values[1][1]) 


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
    #==================================================================================================   
    #values test
    
    xcases = graph_values[0][0]
    ycases = graph_values[1][0]
    xdeaths = graph_values[0][1]
    ydeaths = graph_values[1][1]
    print(xcases)
    print(ycases)
    print(xdeaths)
    print(ydeaths)
    
    
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
    return render_template('chart.html', title='Covid-19 '+country_name, country_name=country_name, max=20000, labels2=line_labels, values2=line_values)

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
    app.run(host='0.0.0.0', port=5000)
