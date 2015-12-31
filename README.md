Stashbot
========

An IRC bot designed to store data in an Elasticsearch cluster.

This bot was created to replace Logstash in an application stack that process
IRC leg messages for:

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
```

Operating the bot
-----------------
```
# Start the bot
$ ./start.sh

# Stop the bot
$ qdel $(job stashbot)
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
