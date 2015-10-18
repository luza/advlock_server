#!/usr/bin/env python

import daemon
import logging
import config
from advlock_server import Server

server = Server(config.bind_addr, config.bind_port)

with daemon.DaemonContext():
    logging.basicConfig(filename=config.log_file,
                        format='%(asctime)s %(message)s')
    try:
        server.start()
    except Exception, e:
        server.stop()
        logging.exception(e)

