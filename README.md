# FlexJoint

 A Python tool intended to simplify integration ceph with openstack

## Building
```bash
# make rpm
```

## Installation
```bash
# rpm -ivh FlexJoint-{release}.x86_64.rpm
```

## Expansion
```bash
# fab add_controller:root@{ip},{password}
# fab add_computer:root@{ip},{password}
```

## 2016.9.24
build1

## 2016.12.20
build2:
Support expansion of controller&computer

## 2017.10.19
build3:
Bugfix, update function:joint_bond_libvirt_ceph

## 2018.11.29 
Version1.1 build1:
- make client name and pool name configurable
- write log to file
