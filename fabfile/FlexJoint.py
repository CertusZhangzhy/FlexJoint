#!/usr/bin/env python
#-*- coding:utf-8 -*-

from joint import *
from testbed.testbed import *

LOG_FILE = './FlexJoint.log'

# redirect stdout to file and itself.
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w')
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def isatty(self):
        return self.terminal.isatty()
    def flush(self):
        self.terminal.flush()

def log_config():
    
    sys.stdout = Logger(LOG_FILE)

def get_control_hosts():
    result = []
    hosts = env.roledefs['controllers']
    for host in hosts:
        result.append((host, env.passwords[host]))
    return result

def get_compute_hosts():
    result = []
    hosts = env.roledefs['computers']
    for host in hosts:
        result.append((host, env.passwords[host]))
    return result

def get_ceph_admin():
    host = env.roledefs['admin'][0]
    return(host, env.passwords[host])

@task
def add_controller(controller_string, controller_password):
    admin_string = get_ceph_admin()[0]
    admin_password = get_ceph_admin()[1]
    VERSION = env.openstack_version
    joint_add_controller(admin_string, admin_password, controller_string, controller_password, VERSION)

@task
def add_computer(computer_string, computer_password):
    admin_string = get_ceph_admin()[0]
    admin_password = get_ceph_admin()[1]
    VERSION = env.openstack_version
    joint_add_computer(admin_string, admin_password, computer_string, computer_password, VERSION)

if __name__=="__main__":

    log_config()
    VERSION = env.openstack_version
    CEPH_DIR = '/etc/ceph'
    OPENSTACK_CONFIG_CMD = 'openstack-config'
    check_client(get_ceph_admin()[0], get_ceph_admin()[1])
    for node in get_control_hosts()+get_compute_hosts():
        check_ceph(node[0], node[1])
        check_cmd(node[0], node[1], OPENSTACK_CONFIG_CMD)
    joint_config_ceph(get_ceph_admin()[0], get_ceph_admin()[1], CEPH_DIR)
    for controller in get_control_hosts():
        joint_distribute_conf_controller(get_ceph_admin()[0], get_ceph_admin()[1], controller[0], controller[1])
        joint_config_controller(controller[0], controller[1], VERSION)
    for computer in get_compute_hosts():
        joint_distribute_conf_computer(get_ceph_admin()[0], get_ceph_admin()[1], computer[0], computer[1])
        joint_config_computer(computer[0],computer[1],VERSION)
    sys.exit(0)
