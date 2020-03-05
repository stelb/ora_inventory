from xml.dom import minidom
import os

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
        proc = subprocess.Popen(["%s/bin/srvctl" % self.gi_home,
                                'config', 'database', '-v'],
                                stdout=subprocess.PIPE)
        dbs_info = proc.stdout.read()
        dbs = dbs_info.splitlines()
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

            proc = subprocess.Popen(['su', user, '-c',
                                    "%s/OPatch/opatch lspatches" % home],
                                    stdout=subprocess.PIPE)
            patch_info = proc.stdout.read()
            patches = patch_info.splitlines()

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

i = Inventory()

i.inventory()
i.dbs()
i.patches()
