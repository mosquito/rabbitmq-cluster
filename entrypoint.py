#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import time
import logging
import re
import socket
from ast import literal_eval
from subprocess import check_call, check_output, Popen, PIPE


def cluster_status():
    return check_output(
        "rabbitmqctl cluster_status", shell=True
    ).decode().splitlines()[0].replace(
        'Cluster status of node', ''
    ).rstrip('.').strip()


def healthcheck():
    prc = Popen("rabbitmqctl -q node_health_check 2>/dev/null", shell=True, stdout=PIPE)
    prc.wait()
    if prc.returncode != 0:
        return False

    return 'Health check passed' in prc.stdout.read().decode()


def check_tcp_port(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))

        return result == 0
    except:
        return False


def main():
    logging.basicConfig(level=logging.INFO)

    vhost = os.getenv('RABBITMQ_DEFAULT_VHOST')


    if vhost is None:
        logging.info("Non cluster mode")
        os.execv('/bin/bash', ['/bin/bash', 'docker-entrypoint.sh', 'rabbitmq-server'])
    else:
        logging.info("Cluster mode")
        process = Popen(['docker-entrypoint.sh', 'rabbitmq-server'])

        while not check_tcp_port('127.0.0.1', 5672):
            logging.info('Waiting local node...')
            time.sleep(1)

        while not healthcheck():
            logging.info("Waiting for...")
            time.sleep(1)

        node_name = cluster_status()

        if node_name in vhost:
            process.wait()
            return exit(process.returncode)

        while not check_tcp_port(vhost, 4369):
            logging.info('Waiting node...')
            time.sleep(1)

        count = 5
        for i in range(count):
            try:
                check_call(['rabbitmqctl', 'stop_app'])

                logging.info("Joining cluster")
                check_call(['rabbitmqctl', 'join_cluster', 'rabbit@%s' % vhost])
                check_call(['rabbitmqctl', 'start_app'])
                break
            except:
                logging.info('Retrying to joining cluster')
                time.sleep(5)
                continue

        process.wait()
        return exit(process.returncode)


if __name__ == '__main__':
    main()
