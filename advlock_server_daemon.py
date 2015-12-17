#!/usr/bin/env python

import daemon
import logging
import config
import pwd
import grp
from lockfile.pidlockfile import PIDLockFile
from advlock_server import Server

handler = logging.FileHandler(config.logfile)
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

server = Server(config.bind_addr, config.bind_port)

with daemon.DaemonContext(uid=pwd.getpwnam(config.user).pw_uid,
                          gid=grp.getgrnam(config.group).gr_gid,
                          pidfile=PIDLockFile(config.pidfile),
                          files_preserve=[handler.stream]):

    logger.info("Daemon started @ %s:%d" % (config.bind_addr, config.bind_port))

    try:
        server.start()
    except Exception, e:
        server.stop()
        logger.exception(e)

