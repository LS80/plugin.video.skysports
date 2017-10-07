# coding=utf-8
##########################################################################
#
#  Copyright 2014-2016 Lee Smith
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
from HTMLParser import HTMLParser

from kodiswift import Plugin, xbmc
from bs4 import BeautifulSoup
import requests


HOST = "http://www.skysports.com"
BASE_PATH = "watch/video/"
BASE_URL = urljoin(HOST, BASE_PATH)

VIDEO_URL_FMT = "http://player.ooyala.com/player/all/{video_id}.m3u8"

PAGE_URL = urljoin(HOST, "common/ajax/articles/{category_id}/{start}/{end}")

VIDEOS_PER_PAGE = 8

plugin = Plugin()

def video_item(video_id, title, thumbnail):
    return {'label': title,
            'thumbnail': thumbnail,
            'path': VIDEO_URL_FMT.format(video_id=video_id),
            'is_playable': True}


def get_categories():
    html = requests.get(BASE_URL).text
    soup = BeautifulSoup(html, 'html.parser')
    for item in soup('a', 'page-nav__link'):
        category = item.string
        if category == 'Featured':
            path = plugin.url_for('featured')
        else:
            path = plugin.url_for('show_videos', path=item['href'].partition(BASE_PATH)[-1])
        yield {'label': category, 'path': path}


def get_category_id(soup):
    load_more = soup.find('div', attrs={"data-fn": "load-more-inline"})
    return re.match("/common/ajax/articles/(\d+)/", load_more['data-url']).group(1)


def get_video_range(category_id, start, end):
    url = urljoin(HOST, PAGE_URL.format(category_id=category_id, start=start, end=end))
    html = requests.get(url).text[1:-1].decode('string_escape').replace('\/', '/')
    soup = BeautifulSoup(html, 'html.parser')

    if start > 1:
        yield {'label': "Previous",
               'path': plugin.url_for('show_video_range', category_id=category_id,
                                      start=max(1, start - VIDEOS_PER_PAGE - 1),
                                      end=start - 1)}

    if soup.find('button', attrs={"data-role": "load-more-button"}):
        yield {'label': "Next",
               'path': plugin.url_for('show_video_range', category_id=category_id,
                                      start=end + 1, end=end + 1 + VIDEOS_PER_PAGE)}

    for video in get_videos(soup):
        yield video


def get_category_videos(path):
    html = requests.get(urljoin(BASE_URL, path)).text
    soup = BeautifulSoup(html, 'html.parser')

    category_id=get_category_id(soup)

    for video in get_video_range(category_id, 1, VIDEOS_PER_PAGE):
        yield video


def get_videos(soup):
    for media in soup('a', {'class': 'polaris-tile__button', 'data-role': None}):
        link = media.find_previous('a', 'polaris-tile__heading-link')
        thumbnail = media.find_previous('img', 'polaris-tile__media')['data-src']

        thumbnail_large = thumbnail.replace('384x216', '768x432')

        m = re.search('/([\w-]+).jpg', thumbnail)
        if m:
            video_id = m.group(1)
            if len(video_id) == 32:
                title = link.get_text().strip()
                yield video_item(video_id, title, thumbnail_large)


@plugin.route('/')
def show_categories():
    return get_categories()


@plugin.route('/category', name='featured')
@plugin.route('/category/<path>')
def show_videos(path=''):
    return get_category_videos(path)


@plugin.route('/category/<category_id>/<start>/<end>')
def show_video_range(category_id, start, end):
    return plugin.finish(get_video_range(category_id, int(start), int(end)),
                         update_listing=True)

if __name__ == '__main__':
    plugin.run()
