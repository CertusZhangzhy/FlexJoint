from fabric.api import env

# hosts info
admin = 'root@172.16.182.124'   # a ceph node with ceph.client.admin.keyring.
controller1 = 'root@172.16.182.124'
computer1 = 'root@172.16.182.124'

#icehouse,kilo,mitaka
env.openstack_version = 'mitaka'

env.roledefs = {
                'admin': [admin],
                'controllers' : [controller1],
                'computers' : [computer1],
                }

# password of each host
env.passwords = {
                admin:'123456',
                controller1:'123456',
                computer1:'123456',
                }

# client name in ceph
env.clients = {
              'glance': 'glance_test',
              'cinder': 'cinder_test',
              }

# pool name in ceph
env.pools = {
            'images': 'images_test',
            'volumes': 'volumes_test',
            'vms': 'vms_test',
            }

# auth string in ceph
# add authority(allow rwx pool={vms}) for FLEXSTACK-864
env.auth = {
           'glance': ("mon 'allow r' osd 'allow class-read object_prefix "
                      "rbd_children, allow rwx pool={images}, allow rwx pool={vms}'".format(images=env.pools['images'],vms=env.pools['vms'])),
           'cinder': ("mon 'allow r' "
		      "osd 'allow class-read object_prefix rbd_children, "
		      "allow rwx pool={images}, allow rwx pool={volumes}, allow rwx pool={vms}'".format(images=env.pools['images'],volumes=env.pools['volumes'],vms=env.pools['vms'])),
           }
