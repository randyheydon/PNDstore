#!/usr/bin/env python2
"""Tests the various core (non-gui-related) elements of pndstore."""
import sys
sys.path.insert(0, '..')

import unittest, shutil, os.path, locale, sqlite3
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


    def testLocale(self):
        #Should return list in desired order, always ending with en_US.
        #If no list is specified, should return (system lang, en_US).
        self.assertEquals(options.get_locale(), [locale.getdefaultlocale()[0], 'en_US'])

        with open(options.get_cfg(), 'w') as cfg:
            cfg.write(
"""[repositories]
1=file://firsturl
[locales]
1=en_CA
2=de_DE""")
        self.assertEquals(options.get_locale(), ['en_CA','de_DE','en_US'])



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
        "major":   4,
        "minor":   2,
        "release": 1,
        "build":   3
      },
      "author":   "Ported by Pickle",
      "vendor":    "dflemstr",
      "uri":       "http://example.org/test.pnd",
      "localizations": {
        "en_US": {
          "title": "Vice xVIC",
          "description": "A VIC Emulator."
        }
      },
      "categories": [
        "Game"
      ],
      "icon":     "http://example.org/test.png"
    },
    {
      "id":        "Different VICE",
      "version": {
        "major":   9,
        "minor":   3,
        "release": 3,
        "build":   6
      },
      "vendor":    "Tempel",
      "uri":       "http://example.org/test2.pnd",
      "localizations": {
        "en_US": {
          "title": "Vice xVIC",
          "description": "A VIC Emulator."
        },
        "en_CA": {
          "title": "Vice xVIC, eh?",
          "description": "It's not prejudice if I'm Canadian, right?!"
        }
      },
      "categories": [
        "Game"
      ],
      "icon":     "http://example.org/test2.png"
    }
  ]
}""")
    
    cfg_text = (
"""[repositories]
1=file://%s
2=file://%s
[locales]
1=en_CA
2=de_DE""")

    def setUp(self):
        options.working_dir = 'temp'

        #Create some local repository files for testing.
        repo_files = ('temp/first.json', 'temp/second.json')
        with open(options.get_cfg(),'w') as cfg:
            cfg.write(self.cfg_text % tuple([os.path.abspath(i) for i in repo_files]) )

        for i in repo_files:
            with open(i,'w') as repo:
                repo.write(self.repotxt % (os.path.basename(i).replace('.',' '), 1.0))

    def tearDown(self):
        shutil.rmtree(options.working_dir)


    def testOpenRepos(self):
        #Maybe this shouldn't be here, since it's more an implementation detail.
        repos = database_update.open_repos()
        #TODO: Check that URIs are... right?


    def testUpdateRemote(self):
        database_update.update_remote()
        db = sqlite3.connect(options.get_database())
        db.row_factory = sqlite3.Row
        #Check that database has correct entries.
        c = db.execute('Select * From "first json"')
        i = c.fetchone()
        self.assertEqual(i['id'], 'viceVIC.pickle')
        self.assertEqual(i['version_major'], 4)
        self.assertEqual(i['version_minor'], 2)
        self.assertEqual(i['version_release'], 1)
        self.assertEqual(i['version_build'], 3)
        self.assertEqual(i['uri'], "http://example.org/test.pnd")
        self.assertEqual(i['title'], "Vice xVIC")
        self.assertEqual(i['description'], "A VIC Emulator.")
        self.assertEqual(i['author'], "Ported by Pickle")
        self.assertEqual(i['vendor'], "dflemstr")
        self.assertEqual(i['icon'], "http://example.org/test.png")
        self.assertEqual(i['icon_cache'], None)
        i = c.fetchone()
        self.assertEqual(i['id'], 'Different VICE')
        self.assertEqual(i['version_major'], 9)
        self.assertEqual(i['version_minor'], 3)
        self.assertEqual(i['version_release'], 3)
        self.assertEqual(i['version_build'], 6)
        self.assertEqual(i['uri'], "http://example.org/test2.pnd")
        self.assertEqual(i['title'], "Vice xVIC, eh?")
        self.assertEqual(i['description'], "It's not prejudice if I'm Canadian, right?!")
        self.assertEqual(i['author'], None)
        self.assertEqual(i['vendor'], "Tempel")
        self.assertEqual(i['icon'], "http://example.org/test2.png")
        self.assertEqual(i['icon_cache'], None)
        #TODO: Test multiple (different!) databases.


    def testBadRemote(self):
        #Test for a malformed JSON file.
        repo0 = os.path.join(options.get_working_dir(),
            os.path.basename(options.get_repos()[0]))
        with open(repo0, 'a') as r: r.write(',')
        self.assertRaises(database_update.RepoError, database_update.update_remote)
        #Test for incorrect version.
        with open(repo0, 'w') as r:
            r.write(self.repotxt % (os.path.basename(repo0), 99.7))
        self.assertRaises(database_update.RepoError, database_update.update_remote)
        #TODO: Test for missing fields, including missing languages.



    def testUpdateLocal(self):
        database_update.update_local()
        #TODO: Check that database has correct entries.



class TestDatabaseQuery(unittest.TestCase):
    pass



class TestFileOperations(unittest.TestCase):
    pass




if __name__=='__main__':
    unittest.main()
