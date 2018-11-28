#!/bin/bash
function check_file()
{
  if [ ! -e $1 ];then
  {
    echo $1 is not available.;
    exit 1
  }
  fi
}

function build_rpm()
{
  [ -d rpmbuild ]&&rm -rf rpmbuild
  make rpm
  if [ $? -eq 0 ];then
  {
    mv rpmbuild/RPMS/x86_64/*.rpm .
    rm -rf rpmbuild
  }
  fi
}

check_file FlexJoint.spec
check_file Makefile
build_rpm
