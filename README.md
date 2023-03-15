Stashbot
========

An IRC bot designed to store data in an Elasticsearch cluster.

This bot was created to replace Logstash in an application stack that
processes IRC messages for:

- [quips](https://github.com/bd808/quips)
- [SAL](https://github.com/bd808/SAL)
- (an as yet unwritten IRC history search system)

In addition to its original Elasticsearch storage purpose, the bot has
expanded to support:
- Updating Phabricator tasks mentioned in `!log` irc massages
- Providing summary information for Phabricator manifest, differential, and
  pholio objects mentioned in irc messages
- Writing `!log` messages to a MediaWiki wiki
- Posting `!log` messages to Twitter
- Posting `!log` messages to Mastodon

Install
-------
```
$ virtualenv virtenv
$ source virtenv/bin/activate
$ pip install -r requirements.txt
```

Configure
---------
The bot is configured using a yaml file. By default `python3 -m stashbot` will
look for a configuration file named `config.yaml`. An alternate file can be
provided using the `--config` cli argument. See `python3 -m stashbot --help`
for more information.

Example configuration:
```
---
irc:
  server: chat.freenode.net
  port: 6697
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
  key: api-xxxxxxxxxxxxxxxxxxxxxxx
  echo: "%(fullName)s - %(uri)s"
  notin:
    - '##somechan'
  delay:
    __default__: 300
    '##somechan': 600

mediawiki:
  wikitech:
    url: https://wikitech.wikimedia.org
    consumer_token: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    consumer_secret: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    access_token: cccccccccccccccccccccccccccccccc
    access_secret: dddddddddddddddddddddddddddddddddddddddd
  otherwiki:
    url: https://wiki.example.com
    consumer_token: 11111111111111111111111111111111
    consumer_secret: 2222222222222222222222222222222222222222
    access_token: 33333333333333333333333333333333
    access_secret: 4444444444444444444444444444444444444444

twitter:
  wikimedia_sal:
    consumer_key: aaaa
    consumer_secret: bbbb
    access_token_key: cccc
    access_token_secret: dddd

mastodon:
  wikimedia_sal:
    url: https://fosstodon.org
    access_token: cccc

bash:
  view_url: https://tools.wmflabs.org/bash/quip/%s

sal:
  view_url: https://tools.wmflabs.org/sal/log/%s
  # For available placeholders, refer to sal.py
  # and look for Logger._store_in_es() and Logger.log()'s bang object.
  phab: "{nav icon=file, name=Mentioned in SAL (%(project)), href=%(href)s} [%(@timestamp)s] <%(nick)s> %(message)s"
  channels:
    '##somechan':
      project: someproject
      wiki: wikitech
      page: Foo/SAL
      category: SAL
      acl:
        default: deny
        allow:
            - *!*@*.example.net
            - *!*@wikimedia/*
    '##anotherchan':
      project: anotherproject
      wiki: otherwiki
      page: Another project logs
      leader: ===
      acl:
        deny:
            - *!*jerk@*.domain
    '##otherchan':
      use_config: '##somechan'
      twitter: wikimedia_sal
      mastodon: wikimedia_sal
```

Operating the bot
-----------------
```
# Start the bot
$ ./bin/stashbot.sh start

# Stop the bot
$ ./bin/stashbot.sh stop

# Tail logs
$ ./bin/stashbot.sh tail
```

License
-------
[GNU GPLv3+](https://www.gnu.org/copyleft/gpl.html "GNU GPLv3+")

Some code and much inspiration taken from:
* [Adminbot](https://phabricator.wikimedia.org/diffusion/ODAC/)
* [Jouncebot](https://phabricator.wikimedia.org/diffusion/GJOU/)
