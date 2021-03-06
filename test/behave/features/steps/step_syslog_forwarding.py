import os
import time
import ast
import socket
import logging
import logging.handlers

import pykafka
from behave import *
from hamcrest import *


@given('"{env_var}" environment variable is "{value}"')
def step_impl(context, env_var, value):
    assert_that(os.environ, has_item(env_var))
    assert_that(os.environ[env_var], equal_to(value))
    context.env[env_var] = os.environ[env_var]


@given('"{env_var}" environment variable is set')
def step_impl(context, env_var):
    assert_that(os.environ, has_item(env_var))
    context.env[env_var] = os.environ[env_var]


@when('sending the syslog message "{message}" in "{sending_format}" format')
def step_impl(context, message, sending_format):
    context.sending_format = sending_format
    context.message = message
    context.message_sent = None
    try:
        logging.info("Sending message \"{0:s}\" to {1:s}:{2:d} in "
            "{3:s} format".format(
                context.message,
                context.server_name,
                logging.handlers.SYSLOG_TCP_PORT,
                context.sending_format
            )
        )
        syslogger = logging.getLogger('syslog')
        syslogger.setLevel(logging.DEBUG)
        syslog_handler = logging.handlers.SysLogHandler(
            address=(
                context.server_name,
                logging.handlers.SYSLOG_TCP_PORT
            ),
            facility=logging.handlers.SysLogHandler.LOG_USER,
            socktype=socket.SOCK_STREAM,
        )
        syslog_handler.append_nul=False
        # Note SysLogHandler TCP doesnt do "Octet-counting" and needs a
        # newline added for "Non-Transparent-Framing". See RFC6587.
        syslog_3164_formatter = logging.Formatter(
            "%(asctime)s behave %(processName)s[%(process)d]: "
            "%(module)s.%(funcName)s: %(message)s\n",
            datefmt='%b %d %H:%M:%S'
            )
        if (sending_format == 'RFC3164'):
            syslog_handler.setFormatter(syslog_3164_formatter)
        elif (sending_format == 'RFC5424'):
            raise NotImplementedError
        else:
            raise ValueError("Unkown format requested")
        syslogger.addHandler(syslog_handler)
        syslogger.info(message)
        context.message_sent = True
    except Exception as e:
        logging.error(
            "Unable to send the message \"{0:s}\" to \"{1:s}\". Exception: "
            "{2:s}".format(
                context.message,
                context.server_name,
                str(e)
            )
        )
        context.message_sent = False
    assert_that(context.message_sent, equal_to(True))


@when('waiting "{timeout}" seconds')
def step_impl(context, timeout):
    time.sleep(float(timeout))


@then('the kafka topic should have the the message within "{timeout}" seconds')
def step_impl(context, timeout):
    message_found = None
    try:
        tls_config = pykafka.SslConfig(
            cafile=getattr(context, 'ca_file'),
            certfile=getattr(context, 'cert_file', None),
            keyfile=getattr(context, 'key_file', None)
        )
        # work arround pain where docker-compose incldues literal quotes within
        # enviroment variables. E.g. var="foo" gets passed as '"foo"' instead
        # of just 'foo'
        broker_list = ','.join(
            ast.literal_eval(context.env['rsyslog_omkafka_broker'])
        )
        client = pykafka.client.KafkaClient(
            hosts=broker_list,
            ssl_config=tls_config
        )
        topic = client.topics[b'test_syslog']
        consumer = topic.get_simple_consumer(
            consumer_timeout_ms=int(timeout) * 1000
        )
        for kafka_message in consumer:
            if kafka_message is not None:
                if context.message in kafka_message.value.decode():
                    message_found = kafka_message.value.decode()
                    break
    except Exception as e:
        logging.error(
            "Unable to search for the message on kafka broker(s) \"{0:s}\" "
            "and topic \"{1:s}\". Exception: {2:s}".format(
                context.env['rsyslog_omkafka_broker'],
                context.env['rsyslog_omkafka_topic'],
                str(e)
            )
        )
    assert_that(message_found, contains_string(context.message))
