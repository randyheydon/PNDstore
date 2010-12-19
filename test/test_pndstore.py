#!/usr/bin/env python2
"""Tests the various core (non-gui-related) elements of pndstore."""
import sys
sys.path.insert(0, '..')

import unittest, shutil, os.path
from pndstore import options, database_update, database_query



class TestOptions(unittest.TestCase):
    def setUp(self):
        options.working_dir = 'temp'
    def tearDown(self):
        shutil.rmtree(options.working_dir)


    def testCopyCfg(self):
        options.get_cfg()
        self.assertEqual(options.get_cfg(), os.path.abspath('temp/pndstore.cfg'))
        self.assertTrue(os.path.isfile(options.get_cfg()))


    def testDatabase(self):
        self.assertEqual(options.get_database(),
            os.path.abspath('temp/app_database.sqlite'))
        #This file doesn't have to exist, because it will be created by the
        #database_update module.  But the directory must exist for the
        #database to be created.
        self.assertTrue(os.path.isdir(options.working_dir))


    def testRepositories(self):
        with open(options.get_cfg(), 'w') as cfg:
            cfg.write(
"""[repositories]
1=firsturl
9=fourthurl
5=thirdurl
4=secondurl""")
        self.assertEqual(options.get_repos(), ['firsturl','secondurl','thirdurl','fourthurl'])



class TestDatabaseUpdate(unittest.TestCase):
    def setUp(self):
        options.working_dir = 'temp'
        repo_files = ('first.json', 'second.json')
        with open(options.get_cfg(),'w') as cfg:
            cfg.write('[repositories]\n1=file:/%s\n2=file:/%s' %
                tuple([os.path.abspath('temp/%s'%i) for i in repo_files]) )
        for i in options.get_repos(): pass

    def tearDown(self):
        shutil.rmtree(options.working_dir)


    def testOpenRepos(self):
        pass


    def testUpdateRemote(self):
        pass


    def testUpdateLocal(self):
        pass



class TestDatabaseQuery(unittest.TestCase):
    pass



class TestFileOperations(unittest.TestCase):
    pass




if __name__=='__main__':
    unittest.main()
