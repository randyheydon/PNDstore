#!/usr/bin/env python2
"""Tests the various core (non-gui-related) elements of pndstore.
For many of these tests to work, libpnd.so.1 must be loadable.  Make sure it's
installed (ie: on a Pandora), or accessible by LD_LIBRARY_PATH."""
import unittest, shutil, os.path, locale, sqlite3

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pndstore import options, database_update, database_query, libpnd

# Latest repo version; only latest gets tested (for now).
repo_version = 2.0

# Find/store files needed for testing here.
testfiles = os.path.join(os.path.dirname(__file__), 'testdata')



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
"""{
    "repositories": [
        "file://firsturl",
        "http://secondurl",
        "ftp://thirdurl",
        "http://fourthurl"
    ],
    "locales": ["default"],
    "searchpath": ["default"]
}""")
        self.assertEqual(options.get_repos(), ['file://firsturl',
            'http://secondurl','ftp://thirdurl','http://fourthurl'])


    def testLocale(self):
        #Should return list in desired order, always ending with en_US.
        #If no list is specified, should return (system lang, en_US).
        self.assertEquals(options.get_locale(), [locale.getdefaultlocale()[0], 'en_US'])

        with open(options.get_cfg(), 'w') as cfg:
            cfg.write(
"""{
    "repositories": [
        "file://firsturl"
    ],
    "locales": [
        "en_CA",
        "de_DE"
    ],
    "searchpath": ["default"]
}""")
        self.assertEquals(options.get_locale(), ['en_CA','de_DE','en_US'])


    def testSearchpath(self):
        # This get_searchpath test is brittle; it'll break if libpnd changes
        # its default behaviour, even though this won't cause problems.
        self.assertItemsEqual(options.get_searchpath(),
            ['/media/*/pandora/apps','/media/*/pandora/desktop',
            '/media/*/pandora/menu','/usr/pandora/apps'],
            "This failure could indicate a change in the behaviour of libpnd, rather than a failure in the Python wrapper.  Check that."
        )

        with open(options.get_cfg(), 'w') as cfg:
            cfg.write(
"""{
    "repositories": [
        "file://firsturl"
    ],
    "locales": ["default"],
    "searchpath": [
        "/lolbuts",
        "/home/places/things/stuff/"
    ]
}""")
        self.assertItemsEqual(options.get_searchpath(), ['/lolbuts',
            '/home/places/things/stuff/']
        )



class TestDatabaseUpdate(unittest.TestCase):
    repotxt = (

# TODO: IMPORTANT.  Get application testing in here.
"""{
  "repository": {
    "name":        "%s",
    "version":     %f
  },
  "packages": [
    {
      "id":        "viceVIC.pickle",
      "version": {
        "major":   "4",
        "minor":   "2",
        "release": "1",
        "build":   "3"
      },
      "author": {
        "name": "Ported by Pickle",
        "website": "http://places.there",
        "email": "one@two.three"
      },
      "vendor":    "dflemstr",
      "uri":       "http://example.org/test.pnd",
      "localizations": {
        "en_US": {
          "title": "Vice xVIC",
          "description": "A VIC Emulator."
        }
      },
      "rating": 12,
      "categories": [
        "Game"
      ],
      "md5": "55538bb9c9ff46699c154d3de733c68b",
      "icon":     "http://example.org/test.png"
    },
    {
      "id":        "Different VICE",
      "version": {
        "major":   "9",
        "minor":   "3b",
        "release": "3",
        "build":   "6"
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
        "Game",
        "Emulator"
      ],
      "md5": "d3de733c68b55538bb9c9ff46699c154",
      "icon":     "http://example.org/test2.png"
    }
  ]
}""")
    
    cfg_text = (
"""{
    "repositories": [
        "file://%%s",
        "file://%%s"
    ],
    "locales": [
        "en_CA",
        "de_DE"
    ],
    "searchpath": ["%(testfiles)s"]
}""" % {'testfiles': testfiles})

    def setUp(self):
        options.working_dir = 'temp'

        #Create some local repository files for testing.
        repo_files = ('temp/first.json', 'temp/second.json')
        with open(options.get_cfg(),'w') as cfg:
            cfg.write(self.cfg_text % tuple(map(os.path.abspath, repo_files)))

        for i in repo_files:
            with open(i,'w') as repo:
                repo.write(self.repotxt % (
                    os.path.basename(i).replace('.',' '), repo_version))

    def tearDown(self):
        shutil.rmtree(options.working_dir)


    def testUpdateRemote(self):
        # TODO: Rewrite this to use testdata/repo.json?
        database_update.update_remote()
        db = sqlite3.connect(options.get_database())
        db.row_factory = sqlite3.Row
        #Check that database has correct entries.
        c = db.execute('Select * From "%s"'%options.get_repos()[0])
        i = c.fetchone()
        self.assertEqual(i['id'], 'viceVIC.pickle')
        self.assertEqual(i['version'], '4.2.1.3')
        self.assertEqual(i['author_name'], "Ported by Pickle")
        self.assertEqual(i['author_website'], "http://places.there")
        self.assertEqual(i['author_email'], "one@two.three")
        self.assertEqual(i['title'], "Vice xVIC")
        self.assertEqual(i['description'], "A VIC Emulator.")
        self.assertEqual(i['icon'], "http://example.org/test.png")
        self.assertEqual(i['uri'], "http://example.org/test.pnd")
        self.assertEqual(i['md5'], '55538bb9c9ff46699c154d3de733c68b')
        self.assertEqual(i['vendor'], "dflemstr")
        self.assertEqual(i['rating'], 12)
        self.assertEqual(i['applications'], None)
        self.assertEqual(i['previewpics'], None)
        self.assertEqual(i['licenses'], None)
        self.assertEqual(i['source'], None)
        self.assertEqual(i['categories'], "Game")
        self.assertEqual(i['icon_cache'], None)
        i = c.fetchone()
        self.assertEqual(i['id'], 'Different VICE')
        self.assertEqual(i['version'], '9.3b.3.6')
        self.assertEqual(i['author_name'], None)
        self.assertEqual(i['author_website'], None)
        self.assertEqual(i['author_email'], None)
        self.assertEqual(i['title'], "Vice xVIC, eh?")
        self.assertEqual(i['description'], "It's not prejudice if I'm Canadian, right?!")
        self.assertEqual(i['icon'], "http://example.org/test2.png")
        self.assertEqual(i['uri'], "http://example.org/test2.pnd")
        self.assertEqual(i['md5'], 'd3de733c68b55538bb9c9ff46699c154')
        self.assertEqual(i['vendor'], "Tempel")
        self.assertEqual(i['rating'], None)
        self.assertEqual(i['applications'], None)
        self.assertEqual(i['previewpics'], None)
        self.assertEqual(i['licenses'], None)
        self.assertEqual(i['source'], None)
        self.assertEqual(i['categories'], "Game:Emulator")
        self.assertEqual(i['icon_cache'], None)
        #TODO: Test multiple (different!) databases.
        #TODO: Test database updating (namely, removal of apps).


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
        #TODO: Test for malformed fields: uri, icon, md5.



    def testUpdateLocal(self):
        database_update.update_local()
        db = sqlite3.connect(options.get_database())
        db.row_factory = sqlite3.Row
        #Check that database has correct entries.
        # TODO: Get some PNDs that have previewpics for testing.
        # TODO: And some with multiple applications.
        c = db.execute('Select * From "%s" Where id="bubbman2"'
            %database_update.LOCAL_TABLE)
        i = c.fetchone()
        self.assertEqual(i['id'], 'bubbman2')
        self.assertEqual(i['version'], '1.0.3.1')
        self.assertEqual(i['author_name'], "pymike")
        self.assertEqual(i['author_website'],
            "http://www.pygame.org/project-BubbMan+2-1114-.html")
        self.assertEqual(i['author_email'], None)
        self.assertEqual(i['title'], "BubbMan2")
        self.assertEqual(i['description'], "A solo entry by pymike for PyWeek #8")
        self.assertEqual(i['icon'], 'data/logo.png')
        self.assertEqual(i['uri'], os.path.join(testfiles, 'BubbMan2.pnd'))
        self.assertEqual(i['md5'], '84c81afa183561f0bb7b2db692646833')
        self.assertEqual(i['vendor'], None)
        self.assertEqual(i['rating'], None)
        self.assertEqual(i['applications'], 'bubbman2')
        self.assertEqual(i['previewpics'], None)
        self.assertEqual(i['licenses'], None)
        self.assertEqual(i['source'], None)
        self.assertEqual(i['categories'], "Game:ActionGame")
        c = db.execute('Select * From "%s" Where id="sparks"'
            %database_update.LOCAL_TABLE)
        i = c.fetchone()
        self.assertEqual(i['id'], 'sparks')
        self.assertEqual(i['version'], '0.4.2.0')
        self.assertEqual(i['author_name'], "Haltux")
        self.assertEqual(i['author_website'], "https://github.com/haltux")
        self.assertEqual(i['author_email'], None)
        self.assertEqual(i['title'], "Sparks")
        self.assertEqual(i['description'], "A vectorial shooter")
        self.assertEqual(i['icon'], 'icon.png')
        self.assertEqual(i['uri'], os.path.join(testfiles, 'Sparks-0.4.2.pnd'))
        self.assertEqual(i['md5'], 'fb10014578bb3f0c0ae8e88a0fd81121')
        self.assertEqual(i['vendor'], None)
        self.assertEqual(i['rating'], None)
        self.assertEqual(i['applications'], 'sparks')
        self.assertEqual(i['previewpics'], None)
        self.assertEqual(i['licenses'], None)
        self.assertEqual(i['source'], None)
        self.assertEqual(i['categories'], "Game:ArcadeGame")
        c = db.execute('Select * From "%s" Where id="the-lonely-tower"'
            %database_update.LOCAL_TABLE)
        i = c.fetchone()
        self.assertEqual(i['id'], 'the-lonely-tower')
        self.assertEqual(i['version'], '2.2.0.0')
        self.assertEqual(i['author_name'], "Randy Heydon")
        self.assertEqual(i['author_website'],
            "http://randy.heydon.selfip.net/Programs/The Lonely Tower/")
        self.assertEqual(i['author_email'], None)
        self.assertEqual(i['uri'], os.path.join(testfiles, 'The Lonely Tower-2.2.pnd'))
        self.assertEqual(i['title'], "The Lonely Tower")
        self.assertEqual(i['description'], "A dumb arty game made for a competition.")
        self.assertEqual(i['categories'], "Game:RolePlaying")
        self.assertEqual(i['vendor'], None)
        self.assertEqual(i['md5'], '0314d0f7055052cd91ec608d63acad2a')
        self.assertEqual(i['icon'],
            'lonelytower/assets/male-brunette-angry-listening-notrans.png')
        # TODO: An individual test for update_local_path.
        # TODO: Test for bad conditions that could cause segfaults.



class TestLibpnd(unittest.TestCase):

    def testConfig(self):
        #This conf_query_searchpath test is brittle; it'll break if libpnd
        #changes its default behaviour, even though this won't cause problems.
        self.assertEqual(libpnd.conf_query_searchpath(),
            '/media/*/pandora/conf:/etc/pandora/conf:./testdata/conf',
            "This failure could indicate a change in the behaviour of libpnd, rather than a failure in the Python wrapper.  Check that.")
        conf = libpnd.conf_fetch_by_name('apps', libpnd.conf_query_searchpath())
        self.assertEqual(libpnd.conf_get_as_char(conf, 'autodiscovery.searchpath'),
            '/media/*/pandora/apps:/media/*/pandora/desktop:/media/*/pandora/menu:/usr/pandora/apps')


    def testDiscovery(self):
        search = libpnd.disco_search(testfiles, None)
        n = libpnd.box_get_size(search)
        self.assertEqual(n, 3)

        node = libpnd.box_get_head(search)
        pnds = [libpnd.box_get_key(node)]
        for i in xrange(n-1):
            node = libpnd.box_get_next(node)
            pnds.append(libpnd.box_get_key(node))
        self.assertItemsEqual(map(os.path.basename, pnds),
            ('BubbMan2.pnd', 'Sparks-0.4.2.pnd', 'The Lonely Tower-2.2.pnd'))


    def testParsing(self):
        pxml = libpnd.pxml_get_by_path(
            os.path.join(testfiles, 'The Lonely Tower-2.2.pnd'))
        self.assertNotEqual(pxml, 0) # Check for failed parsing so we don't segfault.
        for app in pxml:
            if app == 0: break
            self.assertEqual(libpnd.pxml_get_unique_id(app), 'the-lonely-tower')
            self.assertEqual(libpnd.pxml_get_app_name(app, 'en_US'), 'The Lonely Tower')
            libpnd.pxml_delete(app)



class TestDatabaseQuery(unittest.TestCase):
    cfg_text = (
"""{
    "repositories": ["file://%s"],
    "locales": ["default"],
    "searchpath": ["%s"]
}""" % (os.path.abspath(os.path.join(testfiles, 'repo.json')), testfiles))

    def setUp(self):
        options.working_dir = 'temp'
        with open(options.get_cfg(),'w') as cfg:
            cfg.write(self.cfg_text)
        database_update.update_remote()
        database_update.update_local()

    def tearDown(self):
        shutil.rmtree(options.working_dir)


    def testPNDVersion(self):
        v = database_query.PNDVersion
        self.assertGreater(v('2.0.0.0'), v('1.999'))
        self.assertGreater(v('1.1'), v('1.0'))
        self.assertLess(v('2.0a'), v('2.0'))
        self.assertLess(v('2.0'), v('2.1a'))
        self.assertLess(v('2.0a'), v('2.0.1a'))
        self.assertLess(v('2.0a.1'), v('2.0b'))
        self.assertLess(v('1.0.3.1'), v('1.1.2.0'))


    def testGetRemoteTables(self):
        # Okay, this may seem like a gratuitous function, but it gets around
        # DB quoting issues.  This and options.get_repo will not always produce
        # identical results.
        self.assertEquals(database_query.get_remote_tables(),
            options.get_repos())


    def testGetAllAvailable(self):
        database_update.update_local()
        local = database_update.LOCAL_TABLE
        remote = database_query.get_remote_tables()[0]
        with sqlite3.connect(options.get_database()) as db:
            db.row_factory = sqlite3.Row

            r = database_query.get_all_available('the-lonely-tower')
            c = db.execute('Select * From "%s" Where id="the-lonely-tower"'
                % local)
            self.assertEqual(r[0], c.fetchone())
            c = db.execute('Select * From "%s" Where id="the-lonely-tower"'
                % remote)
            self.assertEqual(r[1], c.fetchone())

            r = database_query.get_all_available('bubbman2')
            c = db.execute('Select * From "%s" Where id="bubbman2"'
                % local)
            self.assertEqual(r[0], c.fetchone())
            c = db.execute('Select * From "%s" Where id="bubbman2"'
                % remote)
            self.assertEqual(r[1], c.fetchone())

            # Not installed locally.
            r = database_query.get_all_available('zim')
            self.assertIsNone(r[0])
            c = db.execute('Select * From "%s" Where id="zim"'
                % remote)
            self.assertEqual(r[1], c.fetchone())

            # Not a real package.
            r = database_query.get_all_available('fakeyfakefake')
            self.assertIsNone(r[0])
            self.assertIsNone(r[1])

            # TODO: Test with multiple repos?


    def testGetAllAvailableSorted(self):
        database_update.update_local()
        local = database_update.LOCAL_TABLE
        remote = database_query.get_remote_tables()[0]
        with sqlite3.connect(options.get_database()) as db:
            db.row_factory = sqlite3.Row

            # Same versions.
            r = database_query.get_all_available_sorted('the-lonely-tower')
            c = db.execute('Select * From "%s" Where id="the-lonely-tower"'
                % local)
            self.assertEqual(r[0], c.fetchone())
            c = db.execute('Select * From "%s" Where id="the-lonely-tower"'
                % remote)
            self.assertEqual(r[1], c.fetchone())

            # Newer in repo
            r = database_query.get_all_available_sorted('bubbman2')
            c = db.execute('Select * From "%s" Where id="bubbman2"'
                % remote)
            self.assertEqual(r[0], c.fetchone())
            c = db.execute('Select * From "%s" Where id="bubbman2"'
                % local)
            self.assertEqual(r[1], c.fetchone())

            # Not installed locally.
            r = database_query.get_all_available_sorted('zim')
            c = db.execute('Select * From "%s" Where id="zim"'
                % remote)
            self.assertEqual(r[0], c.fetchone())
            self.assertEqual(len(r), 1)

            # Not a real package.
            r = database_query.get_all_available_sorted('fakeyfakefake')
            self.assertEqual(len(r), 0)

            # TODO: Test with multiple repos?


    def testGetUpdates(self):
        database_query.get_updates()



class TestFileOperations(unittest.TestCase):
    pass




if __name__=='__main__':
    unittest.main()
