Stashbot
========

An IRC bot designed to store data in an Elasticsearch cluster.

This bot was created to replace Logstash in an application stack that processes
IRC messages for:

- [quips](https://github.com/bd808/quips)
- [SAL](https://github.com/bd808/SAL)
- (an as yet unwritten IRC history search system)

Install
-------
```
$ virtualenv virtenv
$ source virtenv/bin/activate
$ pip install -r requirements.txt
```

Configure
---------
The bot is configured using a yaml file. By default `stashbot.py` will look for
a configuration file named `config.yaml`. An alternate file can be provided
using the `--config` cli argument. See `stashbot.py --help` for more
information.

Example configuration:
```
---
irc:
  server: chat.freenode.net
  port: 6667
  nick: mybotnick
  realname: My Real Name
  channels:
    - '##somechan'
    - '##anotherchan'
  ignore:
    - nick1
    - nick2

elasticsearch:
  servers:
    - tools-elastic-01.tools.eqiad.wmflabs
    - tools-elastic-02.tools.eqiad.wmflabs
    - tools-elastic-03.tools.eqiad.wmflabs
  options:
    port: 80
    http_auth:
      - my-es-username
      - my-es-password
    sniff_on_start: false
    sniff_on_connection_fail: false
  index: 'irc-%Y.%m'

ldap:
  uri: ldap://ldap-labs.eqiad.wikimedia.org:389
  base: dc=wikimedia,dc=org

phab:
  url: https://phabricator.wikimedia.org
  user: MyPhabUser
  cert: biglongcerthash
  echo: "%(fullName)s - %(uri)s"

bash:
  view_url: https://tools.wmflabs.org/bash/quip/%s

sal:
  view_url: https://tools.wmflabs.org/sal/log/%s
  phab: "{nav icon=file, name=Mentioned in SAL, href=%(href)s} [%(@timestamp)s] <%(nick)s> %(message)s"
```

Operating the bot
-----------------
```
# Start the bot
$ ./stashbot.sh start

# Stop the bot
$ ./stashbot.sh stop
```

Running with Docker
-------------------
```
$ docker build -t stashbot/stashbot .
$ docker run --name=stashbot -e "CONFIG=test.yaml" -d stashbot/stashbot
$ docker logs --follow stashbot
```

License
-------
[GNU GPLv3+](//www.gnu.org/copyleft/gpl.html "GNU GPLv3+")
