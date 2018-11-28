#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
reload(sys)
import os
import ast
import tempfile
import time

from fabric.api import *
from fabric.contrib import files

def check_ceph(node_string, node_password):
    with settings(host_string = node_string, password = node_password, warn_only = True):
        ret = run('ceph -v')
        if ret.return_code == 127:
            abort('Please install ceph on %s.' % (node_string.split('@')[1]))

def transmit_file(src_string, src_password, dest_string, dest_password, file_name, dest_path):

    with settings(host_string = src_string, password = src_password, warn_only = True):
        if files.exists(file_name):
            get(file_name, '/tmp')
        else:
            pass
    with settings(host_string = dest_string, password = dest_password, warn_only = True):
        if not files.exists(dest_path):
            abort("The dest path:%s is not available." % dest_path)
        tmp_file = '/tmp/'+os.path.split(file_name)[1]
        put(tmp_file, dest_path)
    local('rm -f %s' % tmp_file)

pool_list = ['images','volumes','vms']
keyring_list = ['ceph.client.glance.keyring','ceph.client.cinder.keyring']
key_file_list = ['client.cinder.key','secret.xml','UUID']

joint_auth_string_cinder = ("mon 'allow r' osd 'allow class-read object_prefix "
                        "rbd_children, allow rwx pool=volumes, allow rwx pool=vms, "
                        "allow rwx pool=images'")
                        
joint_auth_string_glance = ("mon 'allow r' osd 'allow class-read object_prefix "
                        "rbd_children, allow rwx pool=images'")

cmd_update_glance = lambda section,key,value:"openstack-config --set /etc/glance/glance-api.conf %s %s %s" % (section, key, value)
cmd_update_cinder = lambda section,key,value:"openstack-config --set /etc/cinder/cinder.conf %s %s %s" % (section, key, value)
cmd_update_nova = lambda section,key,value:"openstack-config --set /etc/nova/nova.conf %s %s %s" % (section, key, value)

def gen_secret_xml_string(uuid):
    script = '''cat > secret.xml <<EOF
<secret ephemeral='no' private='no'>
  <uuid>%s</uuid>
  <usage type='ceph'>
    <name>client.cinder secret</name>
  </usage>
</secret>
EOF''' % uuid
    return script

def backup_conf(file_name):
    backup_file = file_name+".backup_ceph"
    cmd_backup = 'cp %s %s' % (file_name, backup_file)
    cmd_restore = 'cp %s %s' % (backup_file, file_name)
    if files.exists(backup_file):
        run(cmd_restore)
    elif files.exists(file_name):
        run(cmd_backup)
def joint_create_pool(ceph_string, ceph_password, pool_name, pg_num=128):

    with settings(host_string = ceph_string, password = ceph_password, warn_only = True):
        run('ceph osd pool create %s %s' % (pool_name, str(pg_num)))
"""
def joint_create_pool(ceph_string, ceph_password, speed, pool_name, pg_num='128'):

    ""
    speed : 1 high, 0 low
    ""
    script = '/opt/FlexJoint/tools/ceph-crush'
    cmd = './ceph-crush create %s %s %s -p %s' % (pool_name, speed, pg_num, ceph_password)
    with settings(host_string = ceph_string, password = ceph_password, warn_only = True):
        if not files.exists('/etc/ceph/ceph-crush'):
            put(script, '/etc/ceph')
            run('chmod +x /etc/ceph/ceph-crush')
        with cd('/etc/ceph'):
            run(cmd)
"""       

def joint_create_client(ceph_string, ceph_password, client_name, auth_string, ceph_path='/etc/ceph'):

    with settings(host_string = ceph_string, password = ceph_password, warn_only = True):
        cmd_string = 'ceph auth get-or-create client.%s %s | tee %s/ceph.client.%s.keyring' % (client_name, auth_string, ceph_path, client_name)
        run(cmd_string)
    
def joint_generate_cinder_key(ceph_string, ceph_password, ceph_path='/etc/ceph'):

    with settings(host_string = ceph_string, password = ceph_password, warn_only = True):
        file_name = ceph_path+"/"+"client.cinder.key"
        cmd_string = 'ceph auth get-key client.cinder | tee %s' % (file_name)
        run(cmd_string)

def joint_generate_secret_xml(ceph_string, ceph_password, ceph_path='/etc/ceph'):

    with settings(host_string = ceph_string, password = ceph_password, warn_only = True):
        with cd(ceph_path):
            if not files.exists('UUID'):
                uuid = str(run('uuidgen')).strip()
                run("echo %s > UUID" % uuid)
            else:
                uuid = run('cat UUID').strip()
            run(gen_secret_xml_string(uuid))

def joint_bond_libvirt_ceph(computer_string, computer_password, config_path='/etc/ceph'):

    with settings(host_string = computer_string, password = computer_password, warn_only = True):
        with cd(config_path):
            if files.exists('client.cinder.key') and files.exists('secret.xml') and files.exists('UUID'):
                run("virsh secret-undefine `virsh secret-list|awk NR==3|cut -d ' ' -f 2`")
                run("virsh secret-define --file secret.xml")
                uuid = run("cat UUID").strip()
                key = run("cat client.cinder.key").strip()
                cmd = "virsh secret-set-value --secret "+uuid+" --base64 "+key
                run(cmd)
            else:
                abort("[joint_bond_libvirt_ceph]"
                      "Please check your config files under %s." % config_path)

def joint_update_glance_conf_icehouse(controller_string, controller_password, config_path='/etc/glance'):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('service glance-api stop')
        run('service glance-registry stop')
        conf = config_path+'/glance-api.conf'
        backup_conf(conf)
        run("sed -i '0,/^\[DEFAULT\]/a show_image_direct_url = True' "
                "/etc/glance/glance-api.conf")
        run("sed -i '0,/^\[DEFAULT\]/a rbd_store_chunk_size = 8' "
                "/etc/glance/glance-api.conf")
        run("sed -i '0,/^\[DEFAULT\]/a rbd_store_pool = images' "
                "/etc/glance/glance-api.conf")
        run("sed -i '0,/^\[DEFAULT\]/a rbd_store_user = glance' "
                "/etc/glance/glance-api.conf")
        run("sed -i '0,/^\[DEFAULT\]/a default_store = rbd' "
                "/etc/glance/glance-api.conf")
        
def joint_update_glance_conf_kilo(controller_string, controller_password, config_path='/etc/glance'):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('service glance-api stop')
        run('service glance-registry stop')
        conf = config_path+'/glance-api.conf'
        backup_conf(conf)
        run("sed -i 's/^default_store.*/#&/' "
            "/etc/glance/glance-api.conf")
        run("sed -i 's/^filesystem_store_datadir.*/#&/' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[DEFAULT\]/a show_image_direct_url = True' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[glance_store\]/a show_multiple_locations = True' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[glance_store\]/a rbd_store_chunk_size = 8' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[glance_store\]/a rbd_store_ceph_conf = \/etc\/ceph\/ceph.conf' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[glance_store\]/a rbd_store_user = glance' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[glance_store\]/a rbd_store_pool = images' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[glance_store\]/a stores=glance.store.rbd.Store,glance.store.http.Store' "
            "/etc/glance/glance-api.conf")
        run("sed -i '/^\[glance_store\]/a default_store = rbd' "
            "/etc/glance/glance-api.conf")

def joint_update_glance_conf_mitaka(controller_string, controller_password, config_path='/etc/glance'):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('systemctl stop openstack-glance-api')
        run('systemctl stop openstack-glance-registry')
        conf = config_path+'/glance-api.conf'
        backup_conf(conf)
        run(cmd_update_glance('glance_store', 'default_store', 'rbd'))
        run(cmd_update_glance('glance_store', 'stores', 'rbd'))
        run(cmd_update_glance('glance_store', 'rbd_store_pool', 'images'))
        run(cmd_update_glance('glance_store', 'rbd_store_user', 'glance'))
        run(cmd_update_glance('glance_store', 'rbd_store_ceph_conf', r'/etc/ceph/ceph.conf'))
        run(cmd_update_glance('glance_store', 'rbd_store_chunk_size', '8'))

def joint_update_cinder_conf_icehouse(controller_string, controller_password, config_path='/etc/cinder'):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('service cinder-api stop')
        run('service cinder-scheduler stop')
        run('service cinder-volume stop')
        conf = config_path+'/cinder.conf'
        backup_conf(conf)
        run("sed -i '/^\[DEFAULT\]/a glance_api_version=2' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rados_connect_timeout = -1' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_store_chunk_size = 4' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_max_clone_depth = 5' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_flatten_volume_from_snapshot = false' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_ceph_conf = \/etc\/ceph\/ceph.conf' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_pool = volumes' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_user = cinder' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a volume_driver = cinder.volume.drivers.rbd.RBDDriver' "
            "/etc/cinder/cinder.conf")
    
def joint_update_cinder_conf_kilo(controller_string, controller_password, config_path='/etc/cinder'):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('service cinder-api stop')
        run('service cinder-scheduler stop')
        run('service cinder-volume stop')
        conf = config_path+'/cinder.conf'
        backup_conf(conf)
        run("sed -i '/^\[DEFAULT\]/a glance_api_version = 2' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rados_connect_timeout = -1' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_store_chunk_size = 4' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_max_clone_depth = 5' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_flatten_volume_from_snapshot = false' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_ceph_conf = \/etc\/ceph\/ceph.conf' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_pool = volumes' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a rbd_user = cinder' "
            "/etc/cinder/cinder.conf")
        run("sed -i '/^\[DEFAULT\]/a volume_driver = cinder.volume.drivers.rbd.RBDDriver' "
            "/etc/cinder/cinder.conf")

def joint_update_cinder_conf_mitaka(controller_string, controller_password, config_path='/etc/cinder'):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('systemctl stop openstack-cinder-api')
        run('systemctl stop openstack-cinder-scheduler')
        run('systemctl stop openstack-cinder-volume')
        conf = config_path+'/cinder.conf'
        backup_conf(conf)
        run(cmd_update_cinder('DEFAULT', 'enabled_backends', 'ceph'))
        run(cmd_update_cinder('ceph', 'volume_driver', 'cinder.volume.drivers.rbd.RBDDriver'))
        run(cmd_update_cinder('ceph', 'rbd_pool', 'volumes'))
        run(cmd_update_cinder('ceph', 'rbd_user', 'cinder'))
        run(cmd_update_cinder('ceph', 'rbd_ceph_conf', r'/etc/ceph/ceph.conf'))
        run(cmd_update_cinder('ceph', 'rbd_cluster_name', 'ceph'))
        run(cmd_update_cinder('ceph', 'rbd_flatten_volume_from_snapshot', 'false'))
        run(cmd_update_cinder('ceph', 'rbd_max_clone_depth', '5'))
        run(cmd_update_cinder('ceph', 'rbd_store_chunk_size', '4'))
        run(cmd_update_cinder('ceph', 'rados_connect_timeout', '-1'))
        run(cmd_update_cinder('ceph', 'rados_connect_interval', '5'))
        run(cmd_update_cinder('ceph', 'rados_connect_retries', '3'))
        run(cmd_update_cinder('ceph', 'glance_api_version', '2'))

def joint_update_nova_conf_icehouse(computer_string, computer_password, config_path='/etc/nova'):

    with settings(host_string = computer_string, password = computer_password, warn_only = True):
        if not files.exists('/etc/ceph/UUID'):
            abort("[joint_update_nova_conf_icehouse]"
		  "Please check /etc/ceph/UUID.")
        run('systemctl stop libvirtd')
        run('systemctl stop openstack-nova-compute')
        conf=config_path+'/nova.conf'
        backup_conf(conf)
        uuid=str(run('cat /etc/ceph/UUID')).strip()
        run("sed -i '/^\[DEFAULT\]/a rbd_secret_uuid = %s' "
            "/etc/nova/nova.conf" % uuid)
        run("sed -i '/^\[DEFAULT\]/a rbd_user = cinder' "
            "/etc/nova/nova.conf")
        run("sed -i '/^\[DEFAULT\]/a libvirt_images_rbd_ceph_conf = \/etc\/ceph\/ceph.conf' "
            "/etc/nova/nova.conf")
        run("sed -i '/^\[DEFAULT\]/a libvirt_images_rbd_pool = vms' "
            "/etc/nova/nova.conf")
        run("sed -i '/^\[DEFAULT\]/a libvirt_images_type = rbd' "
            "/etc/nova/nova.conf")
            
def joint_update_nova_conf_kilo(computer_string, computer_password, config_path='/etc/nova'):

    with settings(host_string = computer_string, password = computer_password, warn_only = True):
        if not files.exists('/etc/ceph/UUID'):
            abort("[joint_update_nova_conf_kilo]"
                  "Please check /etc/ceph/UUID.")
        run('systemctl stop libvirtd')
        run('service supervisor-nova stop')
        conf=config_path+'/nova.conf'
        backup_conf(conf)
        uuid=str(run('cat /etc/ceph/UUID')).strip()
        run("sed -i '/^\[libvirt\]/a rbd_secret_uuid = %s' "
            "/etc/nova/nova.conf" % uuid)
        run("sed -i '/^\[libvirt\]/a rbd_user = cinder' "
            "/etc/nova/nova.conf")
        run("sed -i '/^\[libvirt\]/a images_rbd_ceph_conf = \/etc\/ceph\/ceph.conf' "
            "/etc/nova/nova.conf")
        run("sed -i '/^\[libvirt\]/a images_rbd_pool = vms' "
            "/etc/nova/nova.conf")
        run("sed -i '/^\[libvirt\]/a images_type = rbd' "
            "/etc/nova/nova.conf")

def joint_update_nova_conf_mitaka(computer_string, computer_password, config_path='/etc/nova'):

    with settings(host_string = computer_string, password = computer_password, warn_only = True):
        if not files.exists('/etc/ceph/UUID'):
            abort("[joint_update_nova_conf_kilo]"
                  "Please check /etc/ceph/UUID.")
        run('systemctl stop libvirtd')
        run('systemctl stop openstack-nova-compute')
        conf=config_path+'/nova.conf'
        backup_conf(conf)
        uuid=str(run('cat /etc/ceph/UUID')).strip()
        run(cmd_update_nova('libvirt', 'images_type', 'rbd'))
        run(cmd_update_nova('libvirt', 'images_rbd_pool', 'vms'))
        run(cmd_update_nova('libvirt', 'images_rbd_ceph_conf', r'/etc/ceph/ceph.conf'))
        run(cmd_update_nova('libvirt', 'rbd_user', 'cinder'))
        run(cmd_update_nova('libvirt', 'rbd_secret_uuid', uuid))
        run(cmd_update_nova('libvirt', 'disk_cachemodes', r'\\"network=writeback\\"'))
        #run(r'''openstack-config --set /etc/nova/nova.conf libvirt disk_cachemodes \\"network=writeback\\"''')<--This also works.
        run(cmd_update_nova('libvirt', 'hw_disk_discard', 'unmap'))
       
def start_controller_icehouse(controller_string, controller_password):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('chown root:glance /etc/glance/glance-api.conf')
        run('service glance-api start')
        run('service glance-registry start')
        run('chown root:cinder /etc/cinder/cinder.conf')
        run('service cinder-api start')
        run('service cinder-volume start')

def start_computer_icehouse(computer_string, computer_password):

    with settings(host_string = computer_string, password = computer_password, warn_only = True):
        run('chown root:nova /etc/nova/nova.conf')
        run('systemctl start libvirtd')
        run('systemctl start openstack-nova-compute')
        
def start_controller_kilo(controller_string, controller_password):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('chown root:glance /etc/glance/glance-api.conf')
        run('service glance-api start')
        run('service glance-registry start')
        run('chown root:cinder /etc/cinder/cinder.conf')
        run('service cinder-api start')
        run('service cinder-volume start')
        run('service cinder-scheduler start')

def start_computer_kilo(computer_string, computer_password):

    with settings(host_string = computer_string, password = computer_password, warn_only = True):
        run('chown root:nova /etc/nova/nova.conf')
        run('systemctl start libvirtd')
        run('service supervisor-nova start')

def start_controller_mitaka(controller_string, controller_password):

    with settings(host_string = controller_string, password = controller_password, warn_only = True):
        run('chown root:glance /etc/glance/glance-api.conf')
        run('systemctl start openstack-glance-api')
        run('systemctl start openstack-glance-registry')
        run('chown root:cinder /etc/cinder/cinder.conf')
        run('systemctl start openstack-cinder-api')
        run('systemctl start openstack-cinder-scheduler')
        run('systemctl start openstack-cinder-volume')

def start_computer_mitaka(computer_string, computer_password):

    with settings(host_string = computer_string, password = computer_password, warn_only = True):
        run('chown root:nova /etc/nova/nova.conf')
        run('systemctl start libvirtd')
        run('systemctl start openstack-nova-compute')
        
def joint_config_ceph(ceph_string, ceph_password, ceph_path='/etc/ceph'):
    """
    1. 创建存储池
    2. 创建client
    3. 生成client.cinder.key及secret.xml
    """
    #joint_create_pool(ceph_string, ceph_password, '1', 'images', '128')
    #joint_create_pool(ceph_string, ceph_password, '0', 'volumes', '128')
    #joint_create_pool(ceph_string, ceph_password, '1', 'vms', '128')

    joint_create_pool(ceph_string, ceph_password, 'images', '128')
    joint_create_pool(ceph_string, ceph_password, 'volumes', '128')
    joint_create_pool(ceph_string, ceph_password, 'vms', '128')

    joint_create_client(ceph_string, ceph_password, 'glance', joint_auth_string_glance, ceph_path)
    joint_create_client(ceph_string, ceph_password, 'cinder', joint_auth_string_cinder, ceph_path)
    joint_generate_cinder_key(ceph_string, ceph_password, ceph_path)
    joint_generate_secret_xml(ceph_string, ceph_password, ceph_path)

def joint_distribute_conf_controller(ceph_string, ceph_password, controller_string, controller_password):
    """
    下发keyring，需要对每个控制节点执行
    """
    file_list = keyring_list
    file_list.append('ceph.conf')
    for file_name in file_list:
        tmp_file = '/etc/ceph/'+file_name
        transmit_file(ceph_string, ceph_password, controller_string, controller_password, tmp_file, '/etc/ceph')
        
def joint_config_controller(controller_string, controller_password, openstack_version):
    """
    配置控制节点并重启glance与cinder相关服务
    """
    if openstack_version.lower() == 'icehouse':
        joint_update_glance_conf_icehouse(controller_string, controller_password, '/etc/glance')
        joint_update_cinder_conf_icehouse(controller_string, controller_password, '/etc/cinder')
        start_controller_icehouse(controller_string, controller_password)
    elif openstack_version.lower() == 'kilo':
        joint_update_glance_conf_kilo(controller_string, controller_password, '/etc/glance')
        joint_update_cinder_conf_kilo(controller_string, controller_password, '/etc/cinder')
        start_controller_kilo(controller_string, controller_password)
    elif openstack_version.lower() == 'mitaka':
        joint_update_glance_conf_mitaka(controller_string, controller_password, '/etc/glance')
        joint_update_cinder_conf_mitaka(controller_string, controller_password, '/etc/cinder')
        start_controller_mitaka(controller_string, controller_password)
        
def joint_distribute_conf_computer(ceph_string, ceph_password, computer_string, computer_password):
    """
    下发UUID，client.cinder.key，client.cinder.keyring及secret.xml到计算节点，需要对每个计算节点执行
    """
    file_list = key_file_list
    file_list.append('ceph.conf')
    file_list.append('ceph.client.cinder.keyring')
    for file_name in file_list:
        tmp_file = '/etc/ceph/'+file_name
        transmit_file(ceph_string, ceph_password, computer_string, computer_password, tmp_file, '/etc/ceph')
        
def joint_config_computer(computer_string, computer_password, openstack_version):
    """
    配置计算节点并重启nova相关服务
    """
    if openstack_version.lower() == 'icehouse':
        joint_bond_libvirt_ceph(computer_string, computer_password, '/etc/ceph')
        joint_update_nova_conf_icehouse(computer_string, computer_password, '/etc/nova')
        start_computer_icehouse(computer_string, computer_password)
    elif openstack_version.lower() == 'kilo':
        joint_bond_libvirt_ceph(computer_string, computer_password, '/etc/ceph')
        joint_update_nova_conf_kilo(computer_string, computer_password, '/etc/nova')
        start_computer_kilo(computer_string, computer_password)
    elif openstack_version.lower() == 'mitaka':
        joint_bond_libvirt_ceph(computer_string, computer_password, '/etc/ceph')
        joint_update_nova_conf_mitaka(computer_string, computer_password, '/etc/nova')
        start_computer_mitaka(computer_string, computer_password)

def joint_add_controller(admin_string, admin_password, controller_string, controller_password, VERSION):
    """
    controller扩容
    """
    check_ceph(controller_string, controller_password)
    joint_distribute_conf_controller(admin_string, admin_password, controller_string, controller_password)
    joint_config_controller(controller_string, controller_password, VERSION)

def joint_add_computer(admin_string, admin_password, computer_string, computer_password, VERSION):
    """
    computer扩容
    """
    check_ceph(computer_string, computer_password)
    joint_distribute_conf_computer(admin_string, admin_password, computer_string, computer_password)
    joint_config_computer(computer_string, computer_password,VERSION)
