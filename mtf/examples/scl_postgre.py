# -*- coding: utf-8 -*-

from mtf.docker import *
from mtf.utils import *
from avocado import Test
import os, time

TIMEOUT = 10

class PostgresqlContainerFactory(Container):
    postgres_image = Image("docker.io/postgres")
    database = "postgres"
    password = "mysecretpassword"
    user = "postgres"
    default_env = "-e POSTGRES_PASSWORD=%s -d %s" % (database, password)

    def __init__(self, docker_params=default_env, start=False):
        super(PostgresqlContainerFactory,self).__init__(self.postgres_image)
        if start:
            self.start(docker_default_params=docker_params)
            time.sleep(TIMEOUT)

    def life_check(self):
        my_env = os.environ.copy()
        my_env["PGPASSWORD"] = self.password
        try:
            run_cmd(["psql", "-h", self.get_ip(), "-c", "SELECT 1", self.database, self.user], env=my_env)
        except subprocess.CalledProcessError:
            return False
        return True


class Basic(Test):
    def test_Pass(self):
        container = PostgresqlContainerFactory(start=True)
        container.life_check()
        container.clean()

    def test_NoOpFails(self):
        self.assertRaises(subprocess.CalledProcessError, PostgresqlContainerFactory, docker_params="", start=True)

    def test_badInvocation(self):
        self.assertRaises(subprocess.CalledProcessError, PostgresqlContainerFactory, docker_params="-v aa:aa", start=True)


class MoreComplexExample(Test):
    def test_connection_between(self):
        master = PostgresqlContainerFactory()
        volume = Volume(facl=['u:26:rwx'])
        master.start(docker_params=master.default_env + " " + volume.docker())
        time.sleep(TIMEOUT)
        self.assertTrue(master.life_check())

        slave = PostgresqlContainerFactory(start=True)
        self.assertTrue(slave.life_check())

        slave.execute("PGPASSWORD=%s psql -h %s -c 'SELECT 1' %s %s" %
                      (master.password, master.get_ip(), master.database, master.user))

        self.assertIn("1", slave.execute("psql -c 'SELECT 1'"))
        master.clean()
        slave.clean()
