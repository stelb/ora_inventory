from xml.dom import minidom
import os
import re

import subprocess

from pwd import getpwuid

class Inventory:
    location = ""
    inventory = ""
    gi_home = ""
    homes = {}
    databases = {}

    def __init__(self):
        with open("/etc/oraInst.loc") as instloc:
            for line in instloc:
                key, value = line.partition("=")[::2]
                if key == "inventory_loc":
                    self.location = value.strip()
        print("inventory: %s\n" % self.location)

    def get_info(self, user, command):
        # execute command as given user and return array of output lines
        print(command)
        #del os.environ["LANG"]
        proc = subprocess.Popen(['su', user, '-c',
                                command],
                                stdout=subprocess.PIPE)
        return proc.stdout.read().splitlines()

    def validatehome(self, inv_loc, home):
        # does home exist?
        if not os.path.isdir(home):
            print("Home: %s does not exist!" % (home))
            return 2
        # inventory move only in /etc/oraInst.loc?
        with open("%s/oraInst.loc" % home) as instloc:
            for line in instloc:
                key, value = line.partition("=")[::2]
                if key == "inventory_loc":
                    home_inv_loc = value.strip()
                    # seems to be 12c feature, so optional
                    if home_inv_loc != self.location:
                        # print("Home: %s wrong inventory location!" % home)
                        return 1
        return 0

    def inventory(self):
        # parse an xml file by name
        inventory = minidom.parse('%s/ContentsXML/inventory.xml' %
                                  self.location)
        homes = inventory.getElementsByTagName('HOME')

        for home in homes:
            name = home.getAttribute('NAME')
            loc = home.getAttribute('LOC')
            crs = home.getAttribute('CRS')
            valid = self.validatehome(self.location, loc)

            self.homes[name] = {}
            self.homes[name]['loc'] = loc
            self.homes[name]['crs'] = crs
            self.homes[name]['valid'] = valid
            if valid < 2:
                user = getpwuid(os.stat("%s/inventory" % loc).st_uid).pw_name
                self.homes[name]['user'] = user
            if crs == 'true':
                self.gi_home = loc

    def dbs(self):
        dbs = self.get_info('root', "%s/bin/srvctl config "
                            "database -v" % self.gi_home)
        for db in dbs:
            (db, home, version) = db.split('\t')
            self.databases[db] = home

    def patches(self):

        for name in self.homes:
            if self.homes[name]['valid'] > 1:
                continue
            home = self.homes[name]['loc']
            user = self.homes[name]['user']
            os.environ["ORACLE_HOME"] = home

            patches = self.get_info(user,
                                       "%s/OPatch/opatch lspatches" % home)

            print(home)
            self.homes[name]['patches'] = {}
            for patch in patches:
                if ";" in patch:
                    (id, comment) = patch.split(';')
                    self.homes[name]['patches'][id] = comment
                    if comment:
                        print("\t%s" % comment)
                    else:
                        print("\t%s" % id)

    def instances(self):
        for name in self.databases:
            home = self.databases[name]
            for n in self.homes:
                if self.homes[n]['loc'] == home:
                    user = self.homes[n]['user']

            os.environ["ORACLE_HOME"] = home
            instances = self.get_info(user, "%s/bin/srvctl "
                                      "status database -d %s" % (home, name))
#            self.databases[name]['instance'] = {}
            # Instance db1 is running on node n3
            re_db_status = re.compile(r'^Instance ([^\W]+)'
                                      ' is running on node (.*)$')
            print(instances)
            for i in instances:
                match = re_db_status.match(i)
                print("%s %s" % (match.group(1), match.group(2)))


i = Inventory()

i.inventory()
i.dbs()
i.patches()
i.instances()
