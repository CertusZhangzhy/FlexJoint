# FlexJoint

 A Python tool intended to simplify integration ceph with openstack

## Building
```
make rpm
```

## Installation
```
rpm -ivh FlexJoint-{release}.x86_64.rpm
```

## Expansion
```
fab add_controller:root@{ip},{password}
fab add_computer:root@{ip},{password}
```

## 2016.9.24
```
build1
```

## 2016.12.20
```
build2:
Support expansion of controller&computer.
```

## 2017.10.19
```
build3:
Bugfix, update function:joint_bond_libvirt_ceph
```
