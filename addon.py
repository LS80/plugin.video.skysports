# coding=utf-8
##########################################################################
#
#  Copyright 2014 Lee Smith
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##########################################################################

import os
import re
from urlparse import urlparse, urlunparse, urljoin
from datetime import timedelta, date
import time
from HTMLParser import HTMLParser
import base64

from xbmcswift2 import Plugin, xbmc
from bs4 import BeautifulSoup
import requests


from resources.lib import http


HOST = "http://www1.skysports.com"
BASE_PATH = "watch/video/sports/"
BASE_URL = urljoin(HOST, BASE_PATH)

F4M_URL_FMT = "http://cf.c.ooyala.com/{id}/{id}_1.f4m"

VIDEO_RE = re.compile('<div class="media.*?<img class="image" src="(.*?/([\w-]+)\.jpg)".*?<h4.*?>(.*?)</h4>.*?>(.*?)<',
                      re.MULTILINE|re.DOTALL)


plugin = Plugin()

def get_f4m_url(video_id):
    return F4M_URL_FMT.format(id=video_id)

def date_from_str(date_str, date_format):
    return date(*(time.strptime(date_str, date_format)[0:3]))
        
def video_item(video_id, title, thumbnail, date_str, date_format="%d/%m/%y"):
    video_date = date_from_str(date_str, date_format)

    title = HTMLParser().unescape(title)

    return {'label': title,
            'thumbnail': thumbnail,
            'path': plugin.url_for('play_video', video_id=video_id),
            'is_playable': True,
            'info': {'title': title,
                     'date': video_date.strftime("%d.%m.%Y")}}

def get_categories():
    html = requests.get(BASE_URL).text
    soup = BeautifulSoup(html, 'html.parser')
    for item in soup('a', {'data-role': 'nav-item'})[1:]:
        category = item.text.strip()
        path = item['href'].partition(BASE_PATH)[-1]
        yield {'label': category,
               'path': plugin.url_for('show_video_list', path=path, page='1')}

def get_videos(path, page, cat_id):
    if cat_id:
        url = urljoin(HOST, "/watch/more/5/{0}/12/{1}".format(cat_id, page))
        html = requests.get(url).text
    else:
        html = requests.get(urljoin(BASE_URL, path)).text

    soup = BeautifulSoup(html, 'html.parser')
    load_more = soup.find('div', attrs={"data-fn": "load-more"})

    if page == 1:
        cat_id = load_more['data-pattern'].split('/')[4]
    else:
        yield {'label': "Previous",
               'path': plugin.url_for('show_video_list', path=path, page=page-1, cat_id=cat_id)}

    if not 'data-end' in load_more.attrs:
        yield {'label': "Next",
               'path': plugin.url_for('show_video_list', path=path, page=page+1, cat_id=cat_id)}

    for media in soup('div', 'media'):
        try:
            thumbnail = media.noscript.img['src']
        except:
            try:
                thumbnail = media.img['data-src']
            except:
                thumbnail = media.img['src']
                thumbnail_large = re.sub("(.*)/30/", "\\1/20/", thumbnail)
            else:
                thumbnail_large = re.sub("(.*)/#{30}/", "\\1/20/", thumbnail)
        else:
            thumbnail_large = thumbnail.replace('402x210', '768x432')

        m = re.search('/([\w-]+).jpg', thumbnail)
        if m:
            video_id = m.group(1)
            if len(video_id) == 32:
                title = media.find('h4').text
                date_str = media.find('p').text
                yield video_item(video_id, title, thumbnail_large, date_str.split()[0])

@plugin.route('/')
def show_categories():
    return get_categories()

@plugin.route('/<path>/page/<page>')
def show_video_list(path, page='1'):
    page = int(page)
    if page > 1:
        cat_id = plugin.request.args['cat_id'][0]
    else:
        cat_id = None
    return get_videos(path, int(page), cat_id)

@plugin.route('/play/<video_id>')
def play_video(video_id):    
    http.run_server_thread()
    livestreamer_url = get_f4m_url(video_id).replace('http', 'hds')
    url = "http://{server}:{port}/{path}".format(server=http.SERVER_NAME,
							                     port=http.SERVER_PORT,
											     path=base64.b64encode(livestreamer_url))
    return plugin.set_resolved_url(url)

if __name__ == '__main__':
    plugin.run()
