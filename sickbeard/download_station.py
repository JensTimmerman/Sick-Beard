# Author: Jens Timmerman <jens.timmerman@gmail.com>
# URL: https://github.com/mr-orange/Sick-Beard
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.
"""
This is an implementation of sickbeards sendTORRENT's api
using the download station WEB API as described here
http://www.synology.com/support/download_station.php?lang=us
"""
import urllib2
import httplib

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard
from sickbeard import logger

ERRORCODES = {
    '100': '100 Unknown error',
    '101': '101 Invalid parameter',
    '102': '102 The requested API does not exist',
    '103': '103 The requested method does not exist',
    '104': '104 The requested version does not support the functionality',
    '105': '105 The logged in session does not have permission',
    '106': '106 Session timeout',
    '107': '107 Session interrupted by duplicate login',
    '400': '400 No such account or incorrect password',
    '401': '401 Guest account disabled',
    '402': '402 Account disabled',
    '403': '403 Wrong password',
    '404': '404 Permission denied',
}


def getsid(host, username, password):
    """Gets a session id from download station
    returns True, sessionid
    or False, errorstring if unsuccessfull
    """

    # url like http://myds.com/webapi/auth.cgi
    host = host + 'webapi'

    # get/post data: api=SYNO.API.Auth&version=2&method=login&account=admin&passwd=12345&session=
    # DownloadStation&format=sid
    post_data = json.dumps({'api': 'SYNO.API.Auth',
                            'version': '2',
                            "method": "login",
                            "account": username,
                            "passwd": password,
                            "session": "DownloadStation",
                            'format': 'sid',
                            })

    request = urllib2.Request(
        url="%s/auth.cgi" % host, data=post_data.encode('utf-8'))

    try:
        response = urllib2.urlopen(request)
    except (EOFError, IOError):
        return False, "Error: Unable to connect to download station (IOError)"
    except httplib.InvalidURL:
        return False, "Error: Invalid download station host"
    except:
        return False, "Error: Unable to connect to download_station"

    try:
        jsonresponse = json.loads(response.read())
        success = jsonresponse['success']
    except KeyError:
        return False, "Error: Invalid response received from download station"

    if success:
        try:
            return True, jsonresponse['data']['sid']
        except:
            return False, "Connection ok, but could not parse sid from response, contact sickbeard developer"
    else:
        errorcode = jsonresponse['error']
        return False, "Received this error from download station: %s" % ERRORCODES[errorcode]


def sendTORRENT(result):
    """Send a torrent url to the downloadstation api"""

    host = sickbeard.TORRENT_HOST + 'json'
    password = sickbeard.TORRENT_PASSWORD
    username = sickbeard.TORRENT_USERNAME

    success, sid = getsid(host, username, password)
    if not success:
        logger.log(
            u"Unable to get download station session ID " + sid, logger.ERROR)
        return False

    # SYNO.DownloadStation.Task&version=1&method=create&uri=ftps://192.0.0.1:2
    # 1/test/test.zip
    post_data = json.dumps({'api': 'SYNO.DownloadStation.task',
                            'version': '1',
                            "method": "create",
                            "_sid": sid,
                            "uri": result.url,
                            "session": "DownloadStation",
                            })

    request = urllib2.Request(
        url="%s/task.cgi" % host, data=post_data.encode('utf-8'))

    logger.log(u"Sending Torrent to Download station Client", logger.DEBUG)

    try:
        request = urllib2.Request(url=host, data=post_data.encode('utf-8'))
        response = urllib2.urlopen(request)
        data = json.loads(response.read())
        if data["success"]:
            logger.log(u"Torrent sent to download station successfully", logger.DEBUG)
            return True
        else:
            logger.log(u"Failure sending Torrent to Download station. error is: " + ERRORCODES[data["error"]],
                       logger.ERROR)
    except Exception, exception:
        logger.log(u"Unknown failure sending Torrent to Deluge", logger.ERROR)
        logger.log("exception: %s" % exception, logger.DEBUG)
        return False


def testAuthentication(host, username, password):
    """Test the authentication to a download station host"""
    success, error = getsid(host, username, password)
    if success:
        return True, "Successfully connected and authenticated to download station"
    return False, error
