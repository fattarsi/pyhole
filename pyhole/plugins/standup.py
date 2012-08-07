#
# Copyright 2012, Piston Cloud Computing, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import random
import re
import time

from datetime import date, timedelta

from pyhole import plugin, utils



class TimeTravelException(Exception):
    pass

def formatted_date(_date=None):
    if not _date:
        _date = date.today()
    return _date.strftime("%Y-%m-%d")


def get_date(_date=None):
    if not _date:
        _date = date.today()
    elif isinstance(_date, str):
        if _date == 'yesterday':
            _date = date.today() - timedelta(1)
        elif _date == 'last week':
            pass
        elif _date == 'tomorrow':
            raise TimeTravelException
        else:
            _date = date.today() - timedelta(int(_date))
    return _date


class Comedian(plugin.Plugin):
    '''A scrum standup plugin.'''

    jokes = None
    date = None

    def load_jokes(self):
        jokes = utils.read_file(self.name, 'jokes.db')
        jokes = "" if jokes is None else jokes
        jokes = jokes.split('\n%')
        return jokes

    def load_clusters(self):
        res = utils.read_file(self.name, 'clusters')
        res = json.loads(res) if res else {}
        return res

    def write_clusters(self, clusters):
        utils.write_file(self.name, 'clusters',
                         json.dumps(clusters))

    def load_scrum(self, _date=None):
        self.date = get_date(_date)

        scrums = utils.read_file(os.path.join(self.name, 'scrums'),
                                 formatted_date(self.date))

        self.scrum_data = scrums.split('\n') if scrums else []

    def write_scrum(self, _date=None):
        if _date:
            _date = get_date(_date)
        else:
            _date = self.date

        scrums = utils.write_file(os.path.join(self.name, 'scrums'),
                                  formatted_date(_date),
                                  str.join('\n', self.scrum_data))
        return scrums

    @plugin.hook_add_command('scrum')
    def scrum(self, params=None, **kwargs):
        '''Get the asynchronous log of the day's activities.
        e.g.)
            scrum [int] => The scrum log for N days ago.
            scrum yesterday => yesteday's scrum log
            scrum lastweek => Last weeks scrum
            scrum lastfriday => Last friday's scrum log.
            scrum tomorrow => tomorrow's scrum log.
        '''

        try:
            self.load_scrum(params)
            if self.scrum_data:
                reply = '\n'.join(self.scrum_data)
            else:
                reply = "I don't have anything for %s" % formatted_date(self.date)
        except TimeTravelException:
            reply = ("Due to lack of experimental evidence on the validity of Novikov's "
                     "self-consistency principle, US Code 29 CFR Part 785.34 regulates "
                     "time travel during the work day. In the event that retro-active "
                     "causality holds across tipler cylinders, you will receive tomorrow's scrum "
                     "yesterday.")
        self.irc.notice(reply)

    @plugin.hook_add_command('standup')
    def standup(self, params=None, **kwargs):
        '''Add yesterday's events.
        '''

        print "WTF"
        self.load_scrum()
        print "WTF"
        if not params:
            self.irc.reply(self.standup.__doc__)
        else:
            nick, mask = self.irc.source.split('!')

            user = re.sub("\W+", '', mask)
            standup_message = "[%s] <%s> %s" % (time.strftime("%H:%M"), user,
                                                params)
            
            self.scrum_data.append(standup_message)
            self.write_scrum()
            self.irc.reply("Got it.")


    @plugin.hook_add_command('reservations')
    def reservations(self, params=None, **kwargs):
        clusters = self.load_clusters()

        for cluster_id, reservation in clusters.items():
            if reservation:
                self.irc.reply('%s by %s at %s' % (cluster_id,
                                                   reservation['name'],
                                                   reservation['time']))
        if not any(clusters.values()):
            self.irc.reply("All clusters are open: %s" % sorted([int(k) for k in clusters.keys()]))
        

    @plugin.hook_add_command('take')
    def take(self, params=None, **kwargs):
        '''Reserve a cluster.

        .take <id> => Create a reservation.
        '''

        clusters = self.load_clusters()

        res = self.take.__doc__
        if params:
            params = params.split(' ')[0]
            cluster_id = unicode(params)

            reservation = clusters.get(cluster_id)

            if reservation is None:
                res = "%s does not exist." % cluster_id
            elif reservation:
                res = "%s is reserved by %s since %s" % (cluster_id,
                                                         reservation.get('name'),
                                                         reservation.get('time'))
            else:
                now = time.strftime("%Y-%m-%d %H:%M")
                nick, mask = self.irc.source.split('!')

                user = re.sub("\W+", '', mask)
                clusters[cluster_id] = {'name': user,
                                        'time': now,}

                self.write_clusters(clusters)
                res = "Reserved %s" % cluster_id
        self.irc.reply(res)

    @plugin.hook_add_command('return')
    def ret(self, params=None, **kwargs):
        ''''''
        clusters = self.load_clusters()

        res = self.ret.__doc__
        if params:
            force = "force" in params
            params = params.split(' ')[0]
            cluster_id = unicode(params)

            reservation = clusters.get(cluster_id)

            if reservation is None:
                res = "%s does not exist." % cluster_id
            else:
                nick, mask = self.irc.source.split('!')

                user = re.sub("\W+", '', mask)
                if user == reservation['name'] or force:
                    clusters[cluster_id] = {}

                    self.write_clusters(clusters)
                    res = "Forced to give up %s." if force else "Gave up %s."
                    res = res % cluster_id
                else:
                    res = "You cannot make me do that."
        self.irc.reply(res)

    @plugin.hook_add_command('cluster')
    def cluster(self, params=None, **kwargs):
        '''Cluster Management.

        .cluster => list clusters
        .cluster add <id> => add a cluster
        .cluster del <id> => delete a cluster
        .cluster take <id> => take a cluster
        .cluster return <id> => return a cluster
        '''

        clusters = self.load_clusters()

        res = []

        avail = lambda x: 'available' if not x else 'reserved'
        res = str.join('\n', sorted([str.join(': ', (_id, avail(res))) for _id, res
                                                               in clusters.items()]))
        if params:
            if params.startswith('add'):
                params = params[4:]  # pop off the command
                params = params.split(' ')[0]
                cluster_id = unicode(params)

                clusters[cluster_id] = {}
                self.write_clusters(clusters)
                res = "Added %s" % cluster_id
            if params.startswith('del'):
                params = params[4:]  # pop off the command
                params = params.split(' ')[0]

                cluster_id = unicode(params)

                clusters.pop(cluster_id, None)
                self.write_clusters(clusters)
                res = "Deleted %s" % cluster_id
            if params.startswith("take"):
                params = params[5:]  # pop off the command
                return self.take(params, **kwargs)
            if params.startswith("return"):
                params = params[7:]  # pop off the command
                return self.ret(params, **kwargs)
        self.irc.reply(res)

    @plugin.hook_add_command('c')
    def alias_c(self, params=None, **kwargs):
        '''Alias of cluster'''
        return self.cluster(params, **kwargs)

    @plugin.hook_add_command('release')
    def alias_return(self, params=None, **kwargs):
        '''Alias of return'''
        return self.ret(params, **kwargs)

    @plugin.hook_add_command('joke')
    def joke(self, params=None, **kw):
        '''Stop me if you've heard this one.'''
        if not self.jokes:
            self.jokes = self.load_jokes()

        joke = random.choice(self.jokes)
        self.jokes.remove(joke)  # Don't tell this joke for a while.

        if not joke:
            joke = "How the fuck am I funny, what the fuck is so funny about me?"
        self.irc.reply(joke)
