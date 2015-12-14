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

Operating the bot
-----------------
```
# Start the bot
$ ./start.sh

# Stop the bot
$ qdel $(job stashbot)
```

License
-------
[GNU GPLv3+](//www.gnu.org/copyleft/gpl.html "GNU GPLv3+")
