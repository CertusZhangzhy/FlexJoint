from fabric.api import env

# hosts info
admin = 'root@172.16.33.11'   # a ceph node with ceph.client.admin.keyring.
controller1 = 'root@10.120.0.5'
controller2 = 'root@10.120.0.6'
controller3 = 'root@10.120.0.9'
computer1 = 'root@10.120.0.7'
computer2 = 'root@10.120.0.8'

#icehouse,kilo,mitaka
env.openstack_version = 'mitaka'

env.roledefs = {
                'admin': [admin],
                'controllers' : [controller1,controller2,controller3],
                'computers' : [computer1,computer2],
                }

# password of each host
env.passwords = {
                admin:'certus_0418',
                controller1:'123456',
                controller2:'123456',
                controller3:'123456',
                computer1:'123456',
                computer2:'123456',
                }
