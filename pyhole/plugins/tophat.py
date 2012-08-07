# Copyright 2012 Christopher MacGown. All Rights Reserved.
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
import random
import time

from pyhole import log
from pyhole import plugin
from pyhole import utils


LOG = log.get_logger('TopHat')


QUOTES = [u"I've always fancied the design and color scheme of the tailwind model.",
          u'And handles like 10-tons of tractor.',
          u"I don't understand this 'ass kicking' reference, sir.",
          u"I have located a weakness in Stane's suit. You must engage up-close proximity.",
          u'That is the only way, sir.',
          u'Oh, joy, sir.',
          u'Power to four-hundred percent capacity.',
          u"I wouldn't consider him a role model.",
          u'Sir, you realize this is a one-way trip?',
          u'May I say how refreshing it is to finally see you on a video with your clothing on, sir.',
          u'I am unable to find a suitable replacement element for the reactor, sir.',
          u'You are running out of time, and options.',
          u'It would appear that the same thing that is keeping you alive is also killing you, sir.',
          u'Just watch me.']


class TopHat(plugin.Plugin):
    ''''''
    teatime_election = {}
    running = False

    def load_teatime(self):
        try:
            self.teatime_election = json.loads(utils.read_file(self.name, 'teatime'))
        except (TypeError, ValueError), e:
            self.teatime_election = {'started': False,
                                     'locations': {}}
            utils.write_file(self.name, 'teatime',
                             json.dumps(self.teatime_election))

    def __locations(self):
        return self.teatime_election['locations']

    def __sorted_votes(self):
        votes = sorted(self.__locations().items(), key=lambda n: len(n[1]),
                                                   reverse=True)

        LOG.error("%s" % votes)
        return votes

    def __suggest(self, location):
        locations = self.__locations()
        for loc in locations.keys():
            if self.irc.source in locations[loc]:
                locations[loc].remove(self.irc.source)
                if not locations[loc]:  # Empty!
                    locations.pop(loc)

        locations[location] = locations.get(location, [])
        locations[location].append(self.irc.source)
        return location


    @plugin.hook_add_command('tophat')
    def tophat(self, params=None, **kwargs):
        '''Return a''' 
        self.irc.reply("Your top hat, sir.")
        return

    @plugin.hook_add_command('suit')
    @utils.admin
    def suit(self, params=None, **kwargs):
        self.irc.reply(random.choice(QUOTES))
        #self.irc.reply("Arc reactor powering up.")

    @plugin.hook_add_command('warmachine')
    def warsuit(self, params=None, **kwargs):
        self.irc.reply(random.choice([q for q in QUOTES 
                                              if not 'sir' in q.lower()]))
        #self.irc.reply("Initiating shitty knock-off suit for the plebs, Sir.")

    @plugin.hook_add_command('teatime')
    def teatime(self, params=None, **kwargs):
        """Start a poll for 'teatime' locations.
            (ex: .teatime start [at] => start a teatime vote for [at] minutes
                                        defaults to 10 minutes.
                 .teatime suggest [location] => suggest a location
                 .teatime [location] => vote for a location)
        """
        self.load_teatime()

        res = []
        run = True
        if params is None:
            if self.teatime_election.get('started'):
                sorted_votes = self.__sorted_votes()
                if sorted_votes:
                    loc, votes = sorted_votes[0]
                    res.append('Currently, your guests would like tea at %s.' % loc)
                else:
                    res.append("Looks like you're taking tea alone, sir.")

            else:
                res.append("You haven't asked for tea, sir.")
        else:
            if 'start' in params:
                if not self.teatime_election.get('started'):
                    try:
                        timer = int(params[5:] if params[5:] else 10)
                    except ValueError:
                        timer = 10
                    timer *= 60

                    self.teatime_election['started'] = True
                    self.teatime_election['timer_expiry'] = time.time() + timer
                    self.teatime_election['locations'] = {}

                    res.append('The sir would like tea?')
                else:
                    res.append('Sir, please be reasonable... '
                               'two teatimes in one day? '
                               'Are you a hobbit?')
            elif 'stop' in params:
                # End the election
                self.irc.reply("My apologies, sir, perhaps it wasn't teatime after all.")

                self.running = False
                utils.write_file(self.name, 'teatime', {'started': False,})
            elif 'suggest' in params:
                params, loc = params.split('suggest')
                loc = loc.strip(' ')

                loc = self.__suggest(loc)

                res.append('Very good, sir, %s is an excellent choice.' % loc)
            elif 'help' in params:
                res.append(self.teatime.__doc__)
                run = False
            else:
                # Assume this is a location.
                loc = self.__suggest(params)

                res.append('Very good, sir, %s is an excellent choice.' % loc)


        utils.write_file(self.name, 'teatime',
                         json.dumps(self.teatime_election))
        self.irc.reply(str.join(' ', res))
        if run and not self.running:
            self.__election()  # Always make sure we have the elector running

    @utils.spawn
    def __election(self):
        if self.running:
            LOG.error("ALREADY RUNNING")
            return

        while True:
            if not self.teatime_election.get('timer_expiry'):
                LOG.debug("No expiry, bailing.")
                break

            self.running = True
            time.sleep(30)

            if time.time() > self.teatime_election['timer_expiry']:
                votes = self.__sorted_votes()
                if votes:
                    loc, votes = votes[0]
                    self.irc.reply("Sir, your guests have chosen %s "
                                   "with %d votes" % (loc, len(votes)))
                break

        # End the election
        self.running = False
        utils.write_file(self.name, 'teatime', {'started': False,})

        return
