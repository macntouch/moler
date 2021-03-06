# -*- coding: utf-8 -*-
"""
One of Moler's goals is to be IO-agnostic.
So it can be used under twisted, asyncio, curio any any other IO system.

Moler's connection is very thin layer binding Moler's ConnectionObserver with external IO system.
Connection responsibilities:
- have a means for sending outgoing data via external IO
- have a means for receiving incoming data from external IO
- perform data encoding/decoding to let external IO use pure bytes
- have a means allowing multiple observers to get it's received data (data dispatching)
"""

__author__ = 'Grzegorz Latuszek, Marcin Usielski, Michal Ernst'
__copyright__ = 'Copyright (C) 2018-2019, Nokia'
__email__ = 'grzegorz.latuszek@nokia.com, marcin.usielski@nokia.com, michal.ernst@nokia.com'

import weakref
import logging
import six
from threading import Lock
from moler.connection import Connection
from moler.connection import identity_transformation
from moler.config.loggers import RAW_DATA, TRACE
from moler.helpers import instance_id


class ObservableConnection(Connection):
    """
    Allows objects to subscribe for notification about connection's data-received.
    Subscription is made by registering function to be called with this data (may be object's method).
    Function should have signature like:

    def observer(data):
        # handle that data
    """

    def __init__(self, how2send=None, encoder=identity_transformation, decoder=identity_transformation,
                 name=None, newline='\n', logger_name=""):
        """
        Create Connection via registering external-IO

        :param how2send: any callable performing outgoing IO
        :param encoder: callable converting data to bytes
        :param decoder: callable restoring data from bytes
        :param name: name assigned to connection
        :param logger_name: take that logger from logging

        Logger is retrieved by logging.getLogger(logger_name)
        If logger_name == "" - take logger "moler.connection.<name>"
        If logger_name is None - don't use logging
        """
        super(ObservableConnection, self).__init__(how2send, encoder, decoder, name=name, newline=newline,
                                                   logger_name=logger_name)
        self._observers = dict()
        self._connection_closed_handlers = dict()
        self._observers_lock = Lock()

    def data_received(self, data):
        """
        Incoming-IO API:
        external-IO should call this method when data is received
        """
        if not self.is_open():
            return
        extra = {'transfer_direction': '<', 'encoder': lambda data: data.encode(encoding='utf-8', errors="replace")}
        self._log_data(msg=data, level=RAW_DATA,
                       extra=extra)

        decoded_data = self.decode(data)
        self._log_data(msg=decoded_data, level=logging.INFO,
                       extra=extra)

        self.notify_observers(decoded_data)

    def subscribe(self, observer, connection_closed_handler):
        """
        Subscribe for 'data-received notification'

        :param observer: function to be called to notify when data received.
        :param connection_closed_handler: callable to be called when connection is closed.
        """
        with self._observers_lock:
            self._log(level=TRACE, msg="subscribe({})".format(observer))
            observer_key, value = self._get_observer_key_value(observer)

            if observer_key not in self._observers:
                self._observers[observer_key] = value
                self._connection_closed_handlers[observer_key] = connection_closed_handler

    def unsubscribe(self, observer, connection_closed_handler):
        """
        Unsubscribe from 'data-received notification'
        :param observer: function that was previously subscribed
        :param connection_closed_handler: callable to be called when connection is closed.
        """
        with self._observers_lock:
            self._log(level=TRACE, msg="unsubscribe({})".format(observer))
            observer_key, _ = self._get_observer_key_value(observer)
            if observer_key in self._observers and observer_key in self._connection_closed_handlers:
                del self._observers[observer_key]
                del self._connection_closed_handlers[observer_key]
            else:
                self._log(level=logging.WARNING,
                          msg="{} and {} were not both subscribed.".format(observer, connection_closed_handler),
                          levels_to_go_up=2)

    def shutdown(self):
        """
        Closes connection with notifying all observers about closing.
        :return: None
        """

        for handler in list(self._connection_closed_handlers.values()):
            handler()
        super(ObservableConnection, self).shutdown()

    def notify_observers(self, data):
        """Notify all subscribed observers about data received on connection"""
        # need copy since calling subscribers may change self._observers
        current_subscribers = list(self._observers.values())
        for self_or_none, observer_function in current_subscribers:
            try:
                self._log(level=TRACE, msg=r'notifying {}({!r})'.format(observer_function, repr(data)))
                try:
                    if self_or_none is None:
                        observer_function(data)
                    else:
                        observer_self = self_or_none
                        observer_function(observer_self, data)
                except Exception:
                    self.logger.exception(msg=r'Exception inside: {}({!r})'.format(observer_function, repr(data)))
            except ReferenceError:
                pass  # ignore: weakly-referenced object no longer exists

    @staticmethod
    def _get_observer_key_value(observer):
        """
        Subscribing methods of objects is tricky::

            class TheObserver(object):
                def __init__(self):
                    self.received_data = []

                def on_new_data(self, data):
                    self.received_data.append(data)

            observer1 = TheObserver()
            observer2 = TheObserver()

            subscribe(observer1.on_new_data)
            subscribe(observer2.on_new_data)
            subscribe(observer2.on_new_data)

        Even if it looks like 2 different subscriptions they all
        pass 3 different bound-method objects (different id()).
        So, to differentiate them we need to "unwind" out of them:
        1) self                      - 2 different id()
        2) function object of class  - all 3 have same id()

        Observer key is pair: (self-id, function-id)
        """
        try:
            self_or_none = six.get_method_self(observer)
            self_id = instance_id(self_or_none)
            self_or_none = weakref.proxy(self_or_none)
        except AttributeError:
            self_id = 0  # default for not bound methods
            self_or_none = None

        try:
            func = six.get_method_function(observer)
        except AttributeError:
            func = observer
        function_id = instance_id(func)

        observer_key = (self_id, function_id)
        observer_value = (self_or_none, weakref.proxy(func))
        return observer_key, observer_value
