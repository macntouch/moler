# -*- coding: utf-8 -*-
"""
Sudo command module.
"""

__author__ = 'Marcin Usielski'
__copyright__ = 'Copyright (C) 2018, Nokia'
__email__ = 'marcin.usielski@nokia.com'

import re

from moler.cmd.unix.genericunix import GenericUnixCommand
from moler.exceptions import CommandFailure
from moler.exceptions import ParsingDone


class Sudo(GenericUnixCommand):

    def __init__(self, connection, sudo_password, cmd_object=None, cmd_class_name=None, cmd_params=None, prompt=None, newline_chars=None, runner=None):
        super(Sudo, self).__init__(connection=connection, prompt=prompt, newline_chars=newline_chars, runner=runner)
        self.sudo_password = sudo_password
        self.cmd_object = cmd_object
        self._sent_sudo_password = False
        self._sent_command_string = False
        self.newline_seq = "\r\n"
        if cmd_class_name:
            params = dict()
            if cmd_params is not None:
                params = cmd_params.copy()
            params["connection"] = connection
            params['prompt'] = prompt
            params["newline_chars"] = newline_chars
            # params["runner"] = runner
        if not self.cmd_object:
            self.set_exception(CommandFailure("Neither 'cmd_class_name' nor 'cmd_object' was provided to Sudo constructor. Please specific parameter."))

    def build_command_string(self):
        cmd = "sudo {}".format(self.cmd_object.command_string)
        return cmd

    def on_new_line(self, line, is_full_line):
        try:
            self._parse_sudo_password(line)
            self._parse_command_not_found(line)
            self._process_embedded_command(line, is_full_line)
        except ParsingDone:
            pass
        super(Sudo, self).on_new_line(line, is_full_line)

    def _process_embedded_command(self, line, is_full_line):
        if not self._sent_command_string:
            self._sent_command_string = True
            cs = "{}{}".format(self.cmd_object.command_string, self.newline_seq)
            self.cmd_object.data_received(cs)
        if is_full_line:
            line = "{}{}".format(line, self.newline_seq)
        self.cmd_object.data_received(line)
        self.current_ret = self.cmd_object.current_ret

    _re_sudo_command_not_found = re.compile(r"sudo:.*command not found")

    def _parse_command_not_found(self, line):
        if re.search(Sudo._re_sudo_command_not_found, line):
            self.set_exception(CommandFailure(self, "Command not found in line '{}'".format(line)))
            raise ParsingDone()

    _re_sudo_password = re.compile(r"\[sudo\] password for.*:", re.I)

    def _parse_sudo_password(self, line):
        if re.search(Sudo._re_sudo_password, line):
            if not self._sent_sudo_password:
                self.connection.sendline(self.sudo_password)
                self._sent_sudo_password = True
            raise ParsingDone()
