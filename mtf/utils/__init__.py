# -*- coding: utf-8 -*-

import string
import random
import logging
import subprocess
import os
import tempfile
import shutil
import re

logger = logging
logger.basicConfig(format='%(levelname)s: Docker : %(message)s', level=logging.DEBUG)

def run_cmd(cmd, raw=False, **kwargs):
    output = None

    if not raw:
        logger.debug("Command: %s" % cmd)
        if isinstance(cmd,str):
            output = subprocess.check_output(cmd.split(" "), **kwargs)
        else:
            output = subprocess.check_output(cmd, **kwargs)
    else:
        logger.debug("Command (raw): %s" % cmd)
        output = subprocess.Popen(cmd, **kwargs)
    return output

def random_str():
    random_size = 10
    return ''.join(random.choice(string.ascii_lowercase)
                   for _ in range(random_size))

class Volume(object):
    target = None
    def __init__(self, directory=None, target=None, permissions=None, facl=[], selinux_type=None, force_selinux=False):
        self.target = target
        self.force_selinux = force_selinux
        if directory:
            self.directory = directory
            if not os.path.exists(self.directory):
                os.makedirs(self.directory)
        else:
            self.directory = tempfile.mkdtemp()
        if permissions:
            self.set_permission(permissions)
        if facl:
            self.set_facl(facl)
        if selinux_type:
            self.set_selinux(selinux_type)

    def set_target(self, target):
        self.target = target

    def set_selinux(self,type):
        run_cmd(["chcon", "-t", type, self.directory])

    def set_force_selinux(self, value):
        self.force_selinux = value

    def set_permission(self,perms):
        run_cmd(["chmod", perms, self.directory])

    def set_facl(self,rules):
        for rule in rules:
            run_cmd(["setfacl", "-m", rule, self.directory])

    def clean(self):
        shutil.rmtree(self.directory)

    def __str__(self):
        return self.directory

    def get_source(self):
        return self.directory

    def get_target(self):
        return self.target

    def get_force_selinux(self):
        return self.force_selinux

    def docker(self):
        if not self.target:
            raise BaseException("target not set for docker")
        output = "-v %s:%s" % (self.directory,self.target)
        if self.force_selinux:
            output += ":Z"
        return output

    def raw(self):
        return self.directory, self.target


def test_volume():
    vol1 = Volume()
    vol1.clean()
    vol2 = Volume()
    assert "/tmp" in str(vol2)
    vol2.clean()

    vol3 = Volume(directory="/tmp/superdir", target="/tmp", permissions="a+x")
    assert "/tmp/superdir" == str(vol3)
    assert "-v /tmp/superdir:/tmp" == vol3.docker()
    vol3.set_force_selinux(True)
    vol3.set_facl(["u:26:rwx"])
    assert "-v /tmp/superdir:/tmp:Z" == vol3.docker()
    vol3.clean()

if __name__ == "__main__":
    test_volume()
