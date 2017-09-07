# -*- coding: utf-8 -*-

import json
import string
import random
import subprocess
import time
import logging
from nose.tools import assert_raises

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

class Image(object):
    def __init__(self, container, tag=None, random_name_size=10):
        self.tag = tag or random_str()
        self.original = container
        self.__import_container()
        self.json = None

    def __import_container(self):
        if ".tar" in self.original:
            run_cmd("docker image import %s %s" % (self.original, self.tag))
            self.original = self.tag
        else:
            if "docker=" in self.original or "docker:" in self.original:
                self.original = self.original[7:]
            else:
                run_cmd("docker image pull %s" % self.original)
            run_cmd("docker image tag %s %s" % (self.original, self.tag))

    def get_tag_name(self):
        return self.tag

    def get_image_name(self):
        return self.original

    def __str__(self):
        return self.tag

    def inspect(self, force=False):
        if force or not self.json:
            output = json.loads(run_cmd("docker image inspect %s" % self.tag))[0]
            self.json = output
            return output
        else:
            return self.json

    def clean(self, force=False):
        run_cmd("docker image remove %s" % self.tag)
        if force and self.tag != self.original:
            run_cmd("docker image remove %s" % self.original)


class Container(object):
    def __init__(self, image, tag=None):
        self.tag = tag or random_str()
        if not isinstance(image, Image):
            raise BaseException("Image is not instance of Image class")
        self.json = None
        self.image = image
        self.docker_id = None
        self.__occupied = False

    def get_tag_name(self):
        return self.tag

    def inspect(self, force=False):
        if force or not self.json:
            output = json.loads(run_cmd("docker container inspect %s" % self.tag))[0]
            self.json = output
            return output
        else:
            return self.json

    def check_running(self):
        json = self.inspect(force=True)["State"]
        if (json["Status"] == "running" and
                not json["Paused"] and
                not json["Dead"]):
            return True
        else:
            return False

    def get_ip(self):
        return self.inspect()["NetworkSettings"]["IPAddress"]

    def start(self, command, docker_default_params="-it -d", **kwargs):
        if not self.docker_id:
            self.__occupied = True
            output = self.run(command, docker_params=docker_default_params, **kwargs)
            self.docker_id = output.split("\n")[-2].strip()
        else:
            raise BaseException("Container already running on background")

    def execute(self, command, **kwargs):
        return run_cmd(["docker", "container", "exec", self.tag, "/bin/bash", "-c", command], **kwargs)

    def run(self, command, docker_params="", **kwargs):
        command = command.split(" ")
        additional_params = docker_params.split(" ") if docker_params else []
        cmdline=["docker", "container", "run","--name", self.tag] + additional_params + [self.image.tag] + command
        output = run_cmd(cmdline, **kwargs)
        if not self.__occupied:
            self.clean()
        return output

    def install_packages(self, packages, command="dnf -y install"):
        if packages:
            logger.debug("installing packages: %s " % packages)
            return self.execute("%s %s" % (command, packages))

    def stop(self):
        if self.docker_id and self.check_running():
            run_cmd("docker stop %s" % self.docker_id)
            self.docker_id = None

    def clean(self):
        self.stop()
        self.__occupied = False
        try:
            run_cmd("docker container rm %s" % self.tag)
        except subprocess.CalledProcessError:
            logger.warning("Container already removed")

    def copy_to(self, src, dest):
        run_cmd("docker cp %s %s:%s" % (src, self.tag, dest))

    def copy_from(self, src, dest):
        self.start()
        run_cmd("docker cp %s:%s %s" % (self.tag, src, dest))


def test_image():
    """
    Image tests. Pull image. check it is able to inspect it

    :return:
    """
    image1 = Image("fedora", tag="ahoj")
    assert image1.inspect().has_key("Config")
    assert "fedora" in image1.get_image_name()
    assert "ahoj" in image1.get_tag_name()
    assert "ahoj" == str(image1)
    image1.clean()

def test_docker():
    """
    Use two images, use them as base for two different containers.
    cont1 is container what does start, will not finish immeadiately
       install package nc inside
       run nc server inside on port 1234
       from host send the message to ip address and port of cont1
       check if message in host arrived

    cont2 run just simple "ls /" command and finish immediatelly
         via assert there is check that sbin is output of command

    :return:
    """
    image1 = Image("fedora", tag="ahoj")
    image2 = Image("fedora", tag="hallo")
    # complex case
    cont1 = Container(image1)
    cont1.start("/bin/bash")
    assert cont1.inspect().has_key("Config")
    assert cont1.check_running()
    assert "172" in cont1.get_ip()
    assert "sbin" in cont1.execute("ls /")
    cont1.install_packages("nc")
    bckgrnd = cont1.execute("nohup nc -l 1234", raw=True, stdout=subprocess.PIPE)
    time.sleep(1)
    bckgrnd2 = run_cmd(["nc", cont1.get_ip(), "1234"], raw=True, stdin=subprocess.PIPE)
    bckgrnd2.communicate(input="ahoj")
    assert "ahoj" in bckgrnd.communicate()[0]
    cont1.stop()
    cont1.clean()
    # simplier case
    cont2 = Container(image2)
    assert "sbin" in cont2.run("ls /")
    # test if raise is raised in case nonexisting command
    assert_raises(subprocess.CalledProcessError, cont2.run,"nonexisting command")

    # test if raise is raised in case bad volume mapping
    assert_raises(subprocess.CalledProcessError, cont2.run, "ls /", docker_params="-v abc:cba")




if __name__ == "__main__":
    test_image()
    test_docker()
