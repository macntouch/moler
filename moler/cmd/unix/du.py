# -*- coding: utf-8 -*-
"""
du command module.
"""

__author__ = 'Marcin Szlapa'
__copyright__ = 'Copyright (C) 2019, Nokia'
__email__ = 'marcin.szlapa@nokia.com'

from moler.cmd.unix.genericunix import GenericUnixCommand
from moler.exceptions import ParsingDone
import re


class Du(GenericUnixCommand):
    """Unix command du."""

    def __init__(self, connection, options=None, prompt=None, newline_chars=None, runner=None):
        """
        Unix command du.

        :param connection: moler connection to device, terminal when command is executed
        :param options: Options of unix du command
        :param prompt: expected prompt sending by device after command execution
        :param newline_chars: Characters to split lines
        :param runner: Runner to run command
        """
        super(Du, self).__init__(connection=connection, prompt=prompt, newline_chars=newline_chars,
                                 runner=runner)
        self.options = options
        self.current_ret = dict()

    def build_command_string(self):
        """
        Build command string from parameters passed to object.

        :return: String representation of command to send over connection to device.
        """
        cmd = "du"
        if self.options:
            cmd = '{} {}'.format(cmd, self.options)
        return cmd

    def on_new_line(self, line, is_full_line):
        """
        Put your parsing code here.

        :param line: Line to process, can be only part of line. New line chars are removed from line.
        :param is_full_line: True if line had new line chars, False otherwise
        :return: Nothing
        """
        if is_full_line:
            try:
                self._parse_du(line)
            except ParsingDone:
                pass
        return super(Du, self).on_new_line(line, is_full_line)

    # 4       ./directory/directory2
    _re_du = re.compile(r"(?P<NUMBER>^\d+)\s+(?P<DIRECTORY>\S*$)")

    def _parse_du(self, line):
        if self._regex_helper.search_compiled(Du._re_du, line):
            self.current_ret[self._regex_helper.group('DIRECTORY')] = int(
                self._regex_helper.group('NUMBER'))
            raise ParsingDone


COMMAND_OUTPUT_DU = """host:~ # du
4       ./directory/directory2
8       ./directory
12      .
host:~ #"""

COMMAND_KWARGS_DU = {
}

COMMAND_RESULT_DU = {
    "./directory/directory2": 4,
    "./directory": 8,
    ".": 12
}

COMMAND_OUTPUT_DU_SK = """host:~ # du -sk *
0       file
8       directory
host:~ #"""

COMMAND_KWARGS_DU_SK = {
    "options": "-sk *"
}

COMMAND_RESULT_DU_SK = {
    "file": 0,
    "directory": 8,
}
