# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab

"""
tests.test_main
~~~~~~~~~~~~~~~

Provides unit tests for the website.
"""

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

import nose.tools as nt
import logging
import sys
import pygogo as gogo

from StringIO import StringIO
from json import loads
from . import BaseTest

module_logger = gogo.Gogo(__name__).logger
nt.assert_equal_ellipsis = BaseTest().assertEqualEllipsis
nt.assert_is_subset = BaseTest().assertIsSubset
nt.assert_is_not_subset = BaseTest().assertIsNotSubset


def setup_module():
    """site initialization"""
    global initialized
    initialized = True
    module_logger.debug('Main module setup\n')


class TestMain(BaseTest):
    """Main unit tests"""
    cls_initialized = False

    def setUp(self):
        nt.assert_false(self.cls_initialized)
        self.cls_initialized = True
        module_logger.debug('TestMain class setup\n')

    def tearDown(self):
        nt.ok_(self.cls_initialized)
        module_logger.debug('TestMain class teardown\n')

    def test_handlers(self):
        f = StringIO()
        hdlr = gogo.handlers.fileobj_hdlr(f)
        lggr = gogo.Gogo('test_handlers', high_hdlr=hdlr).logger

        msg1 = 'stdout hdlr only'
        lggr.debug(msg1)
        f.seek(0)
        nt.assert_equal(sys.stdout.getvalue().strip(), msg1)
        nt.assert_false(f.read())

        msg2 = 'both hdlrs'
        lggr.error(msg2)
        f.seek(0)
        nt.assert_equal(sys.stdout.getvalue().strip(), '%s\n%s' % (msg1, msg2))
        nt.assert_equal(f.read().strip(), msg2)

    def test_multiple_loggers(self):
        f = StringIO()

        going = gogo.Gogo(
            'myapp',
            low_hdlr=gogo.handlers.fileobj_hdlr(f),
            low_formatter=gogo.formatters.fixed_formatter,
            high_hdlr=gogo.handlers.stdout_hdlr(),
            high_level='info',
            high_formatter=gogo.formatters.console_formatter)

        root = going.logger
        logger1 = going.get_logger('area1')
        logger2 = going.get_logger('area2')

        root.info('Jackdaws love my big sphinx of quartz.')
        logger1.debug('Quick zephyrs blow, vexing daft Jim.')
        logger1.info('How quickly daft jumping zebras vex.')
        logger2.warning('Jail zesty vixen who grabbed pay.')
        logger2.error('The five boxing wizards jump quickly.')

        console_msg = (
            "myapp.base  : INFO     Jackdaws love my big sphinx of quartz."
            "\nmyapp.area1 : INFO     How quickly daft jumping zebras vex."
            "\nmyapp.area2 : WARNING  Jail zesty vixen who grabbed pay."
            "\nmyapp.area2 : ERROR    The five boxing wizards jump quickly.")

        file_msg = [
            "myapp.base   INFO     Jackdaws love my big sphinx of quartz.\n",
            "myapp.area1  DEBUG    Quick zephyrs blow, vexing daft Jim.\n",
            "myapp.area1  INFO     How quickly daft jumping zebras vex.\n",
            "myapp.area2  WARNING  Jail zesty vixen who grabbed pay.\n",
            "myapp.area2  ERROR    The five boxing wizards jump quickly.\n"]

        f.seek(0)
        nt.assert_equal(console_msg, sys.stdout.getvalue().strip())
        nt.assert_equal([line[24:] for line in f], file_msg)

    def test_params_and_looping(self):
        levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        f = StringIO()
        going = gogo.Gogo(low_hdlr=gogo.handlers.fileobj_hdlr(f))
        logger1 = going.get_logger('area1')
        logger2 = gogo.Gogo().get_logger('area2')

        logger1_msg = 'A debug message\nAn info message'
        logger1.debug('A debug message')
        logger1.info('An info %s', 'message')
        f.seek(0)
        nt.assert_equal(f.read().strip(), logger1_msg)
        logger2_msg = ''

        for level in [getattr(logging, l) for l in levels]:
            name = logging.getLevelName(level)
            logger2_msg += '%s message\n' % name
            logger2.log(level, '%s %s', name, 'message')
            # TODO: lookup yielding from a nose test

        nt.assert_equal(sys.stdout.getvalue().strip(), logger2_msg.strip())

    def test_structured_formatter(self):
        console_msg = (
            '{"snowman": "\\u2603", "name": "root.base", "level": "INFO",'
            ' "message": "log message", "time": "2015", "msecs": ..., '
            '"set_value": [1, 2, 3]}')

        log_format = gogo.formatters.BASIC_FORMAT
        kwargs = {'datefmt': '%Y'}
        formatter = gogo.formatters.StructuredFormatter(log_format, **kwargs)
        kwargs = {'low_level': 'info', 'low_formatter': formatter}
        logger = gogo.Gogo(**kwargs).logger
        extra = {'set_value': set([1, 2, 3]), 'snowman': '\u2603'}
        logger.info('log message', extra=extra)
        nt.assert_equal_ellipsis(console_msg, sys.stdout.getvalue().strip())

    def test_structured_logging(self):
        kwargs = {'persist': True}
        extra = {'additional': True}
        details = set(['level', 'name', 'time'])

        # Basic structured logger
        logger0 = gogo.Gogo('logger0').get_structured_logger('base', **kwargs)

        # Structured logger
        formatter = gogo.formatters.structured_formatter
        logger1 = gogo.Gogo('logger1', low_formatter=formatter).logger

        # Structured logger
        formatter = gogo.formatters.json_formatter
        logger2 = gogo.Gogo('logger2', low_formatter=formatter).logger

        # Structured logger that allows for custom format
        log_frmt = (
            '{"time": "%(asctime)s.%(msecs)d", "name": "%(name)s", "level":'
            ' "%(levelname)s", "message": "%(message)s", '
            '"persist": "%(persist)s", "additional": "%(additional)s"}')

        going = gogo.Gogo('logger3', low_formatter=logging.Formatter(log_frmt))
        logger3 = going.get_logger(**kwargs)

        # Now log some messages
        for logger in [logger0, logger1, logger2, logger3]:
            logger.debug('message', extra=extra)

        lines = sys.stdout.getvalue().strip().split('\n')
        results = map(loads, lines)

        # Assert the following loggers provide the log event details
        nt.assert_is_not_subset(details, results[0])
        nt.assert_is_subset(details, results[1])
        nt.assert_is_subset(details, results[2])
        nt.assert_is_subset(details, results[3])

        # Assert the following loggers provide the `extra` information
        nt.assert_in('additional', results[0])
        nt.assert_in('additional', results[1])
        nt.assert_not_in('additional', results[2])
        nt.assert_in('additional', results[3])

        # Assert the following loggers provide the `persist` information
        nt.assert_in('persist', results[0])
        nt.assert_in('persist', results[1])
        nt.assert_not_in('persist', results[2])
        nt.assert_in('persist', results[3])

        # Assert the following loggers provide the `msecs` in the time
        nt.assert_false(len(results[0].get('time', [])))
        nt.assert_false(len(results[1]['time'][20:]))
        nt.ok_(len(results[2]['time'][20:]))
        nt.ok_(len(results[3]['time'][20:]))
