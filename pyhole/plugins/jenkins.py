#   Copyright 2012 Josh Kearney
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Pyhole Jenkins Plugin"""

import commands
import json
import time

from lxml import etree

from pyhole import plugin
from pyhole import utils


class Jenkins(plugin.Plugin):
    """Provide access to common Jenkins functionality."""

    @plugin.hook_add_poll("poll_bad_builds")
    def poll_bad_builds(self, params=None, **kwargs):
        rss = read_url("https://albino.pistoncloud.com/rssFailed")
        try:
            tree = etree.fromstring(rss)
        except etree.XMLSyntaxError, e:
            self.irc.log.debug(e)
            return

        namespaces = {"atom": "http://www.w3.org/2005/Atom"}
        new_failures = {}
        for entry in tree.xpath("//atom:entry", namespaces=namespaces):
            title = entry.xpath(".//atom:title/text()", namespaces=namespaces)[0]
            url = entry.xpath(".//atom:link", namespaces=namespaces)[0].attrib["href"]

            try:
                repo_json = json.loads(read_url(url + "api/json"))
                owner, branch = parse_params(repo_json["actions"][0]["parameters"])
            except Exception, e:
                self.irc.log.debug(e)
                continue

            title = title + " - %s/%s" % (owner, branch)
            new_failures[title] = url

        try:
            old_failures = self._read_cache()
        except Exception:
            self.irc.log.info("Jenkins RSS cache doesn't exist; writing")
            self._write_cache(new_failures)
            return

        for new_failure in list(set(new_failures) - set(old_failures)):
            title = str(new_failure)
            url = new_failures[new_failure]
            reply = "[BUILD FAILED] %s: %s" % (title, url)
            self.irc.notice(reply)
            time.sleep(1)

        self._write_cache(new_failures)

    def _write_cache(self, data):
        """Write RSS data to cache file."""
        json_data = json.dumps(data)
        utils.write_file(self.name, "rss_cache", json_data)

    def _read_cache(self):
        """Read RSS cache data."""
        rss_cache = utils.read_file(self.name, "rss_cache")
        return json.loads(rss_cache)


def read_url(url):
    user = "pyhole"
    api_key = "W6YEcvk2CkuD"
    # NOTE(jk0): I know, but I didn't feel like hacking things to get
    # around the SSL errors that urllib2 was throwing.
    wget_command = "wget -qO- --secure-protocol=SSLv3 --no-check-certificate --auth-no-challenge --http-user=%s --http-password=%s %s" % (user, api_key, url)

    return commands.getoutput(wget_command)


def parse_params(params):
    owner = None
    branch = None

    for param in params:
        if param["name"] == "GITHUB_OWNER":
            owner = param["value"]
        elif param["name"] == "GITHUB_BRANCH":
            branch = param["value"]

    return (owner, branch)
