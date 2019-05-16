# -*- coding: utf-8 -*-
__author__ = 'Marcin Usielski'
__copyright__ = 'Copyright (C) 2019, Nokia'
__email__ = 'marcin.usielski@nokia.com'

import datetime
import re
from dateutil import parser

from moler.events.textualevent import TextualEvent
from moler.exceptions import ParsingDone


class LastLogin(TextualEvent):
    def __init__(self, connection, till_occurs_times=-1, runner=None):
        """
        Event for 'Last login ... from ...'

        :param connection: moler connection to device, terminal when command is executed
        :param till_occurs_times: number of event occurrence
        :param runner: Runner to run event
        """
        super(LastLogin, self).__init__(connection=connection, runner=runner, till_occurs_times=till_occurs_times)
        self.current_ret = dict()

    def on_new_line(self, line, is_full_line):
        """
        Put your parsing code here.

        :param line: Line to process, can be only part of line. New line chars are removed from line.
        :param is_full_line: True if line had new line chars, False otherwise
        :return: Nothing
        """
        if is_full_line:
            try:
                self._parse_last_login(line=line)
            except ParsingDone:
                pass

    # Last login: Tue Jun 12 08:54:44 2018 from 127.0.0.1
    _re_last_login = re.compile(r'Last login:\s+(?P<DATE>\S.*\S)\s+from\s+(?P<HOST>\S+)', re.I)

    def _parse_last_login(self, line):
        if self._regex_helper.search(LastLogin._re_last_login, line):
            self.current_ret["time"] = datetime.datetime.now()
            self.current_ret["host"] = self._regex_helper.group("HOST")
            date_str = self._regex_helper.group("DATE")
            self.current_ret["date_raw"] = date_str
            self.current_ret["date"] = parser.parse(date_str)
            self.event_occurred(event_data=self.current_ret)
            self.current_ret = dict()
            raise ParsingDone()


EVENT_OUTPUT = """
Last login: Tue Jun 12 08:54:44 2018 from 127.0.0.1
"""

EVENT_KWARGS = {
    "till_occurs_times": 1
}

EVENT_RESULT = [
    {
        'time': datetime.datetime(2019, 1, 14, 13, 12, 48),
        'host': '127.0.0.1',
        'date_raw': 'Tue Jun 12 08:54:44 2018',
        'date': datetime.datetime(2018, 6, 12, 8, 54, 44),
    }
]
