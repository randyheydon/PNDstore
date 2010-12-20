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


    def testWorkingDir(self):
        #Ensure the full returned path is in this test directory.
        self.assertEqual(options.get_working_dir()[-9:], 'test/temp')


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
        self.assertTrue(os.path.isdir(options.get_working_dir()))


    def testRepositories(self):
        with open(options.get_cfg(), 'w') as cfg:
            cfg.write(
"""[repositories]
1=file://firsturl
9=http://fourthurl
5=ftp://thirdurl
4=http://secondurl""")
        self.assertEqual(options.get_repos(), ['file://firsturl',
            'http://secondurl','ftp://thirdurl','http://fourthurl'])



class TestDatabaseUpdate(unittest.TestCase):
    repotxt = (

"""{
  "repository": {
    "name":        "%s",
    "version":     %f
  },
  "applications": [
    {
      "id":        "viceVIC.pickle",
      "version": {
        "major":   2,
        "minor":   2,
        "release": 0,
        "build":   0
      },
      "author":   "Ported by Pickle",
      "vendor":    "dflemstr",
      "uri":       "http://dflemstr.dyndns.org:8088/file/package/WPL5JKWK0PTODSWK.pnd",
      "localizations": {
        "en_US": {
          "title": "Vice xVIC",
          "description": "A VIC Emulator."
        }
      },
      "categories": [
        "Game"
      ],
      "icon":     "http://dflemstr.dyndns.org:8088/file/image/WPL5JKWK0PTODSWK.png"
    }
  ]
}""")
    
    def setUp(self):
        options.working_dir = 'temp'

        #Create some local repository files for testing.
        repo_files = ('temp/first.json', 'temp/second.json')
        with open(options.get_cfg(),'w') as cfg:
            cfg.write('[repositories]\n1=file://%s\n2=file://%s' %
                tuple([os.path.abspath(i) for i in repo_files]) )

        for i in repo_files:
            with open(i,'w') as repo:
                repo.write(self.repotxt % (os.path.basename(i), 1.0))

    def tearDown(self):
        shutil.rmtree(options.working_dir)


    def testOpenRepos(self):
        #Maybe this shouldn't be here, since it's more an implementation detail.
        repos = database_update.open_repos()
        #TODO: Check that URIs are... right?


    def testUpdateRemote(self):
        database_update.update_remote()
        #TODO: Check that database has correct entries.


    def testBadRemote(self):
        #Test for a malformed JSON file.
        repo0 = os.path.join(options.get_working_dir(),
            os.path.basename(options.get_repos()[0]))
        with open(repo0, 'a') as r: r.write(',')
        self.assertRaises(database_update.RepoError, database_update.update_remote)
        #Test for incorrect version.
        with open(repo0, 'w') as r:
            r.write(self.repotxt % (os.path.basename(repo0), 1.3))
        self.assertRaises(database_update.RepoError, database_update.update_remote)
        #TODO: Test for missing fields.



    def testUpdateLocal(self):
        database_update.update_local()
        #TODO: Check that database has correct entries.



class TestDatabaseQuery(unittest.TestCase):
    pass



class TestFileOperations(unittest.TestCase):
    pass




if __name__=='__main__':
    unittest.main()
