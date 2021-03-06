Feature: Process timestamps with or without timezone information

  In order to process syslog messages from multiple systems
  As a log collection service
  I want the service to be able to handle various timestamps
    And to apply the local syslog servers timezone applies to the source if the source message lacked timezone information (e.g. RFC3164)
    And to map and translate the original timezone information if the source message included timezone information (e.g. RFC5424)

  Background: Syslog service is available
    Given a valid rsyslog configuration
      And a server "test_syslog_server"
      And an environment variable file "test_syslog_server.env"
      And "TZ" environment variable is "Africa/Johannesburg"


    @slow
    Scenario Outline: Local timezone applies to messages that omit timezone info
    Given a protocol "TCP" and port "514"
      And "rsyslog_omfwd_json_template" environment variable is "TmplJSONRawMeta"
      And a file "/tmp/json_relay/nc.out"
    When connecting
      And sending the raw message "<message>"
      And waiting "1" seconds
      And searching lines for the pattern "<regex>" over "30" seconds
    Then a connection should be complete
      And the pattern should be found
      And a JSON entry should contain "<json>"

    Examples:
      | message | regex | json |
      | <14>Jan 1 02:43:29 behave test[99999]: RFC3164 without timezone info | .*?RFC3164 without timezone info.* | { "timestamp": "2018-01-01T02:43:29+02:00" } |

    @slow
    Scenario Outline: Process and retain timezone info
    Given a protocol "TCP" and port "514"
      And "rsyslog_omfwd_json_template" environment variable is "TmplJSONRawMeta"
      And a file "/tmp/json_relay/nc.out"
    When connecting
      And sending the raw message "<message>"
      And waiting "1" seconds
      And searching lines for the pattern "<regex>" over "30" seconds
    Then a connection should be complete
      And the pattern should be found
      And a JSON entry should contain "<json>"

    Examples:
      | message | regex | json |
      | <14>1 2017-09-19T23:43:29.737941+02:00 behave test 99999 - RFC5424 with numeric timezone offset for SAST | .*?RFC5424 with numeric timezone offset for SAST.* | { "timestamp": "2017-09-19T23:43:29.737941+02:00" } |
      | <14>1 2017-09-17T23:43:29.737941Z behave test 99999 - RFC5424 with UTC timezone | .*?RFC5424 with UTC timezone.* | { "timestamp": "2017-09-17T23:43:29.737941Z" } |
