#!/usr/bin/env python2
"""Tests the various core (non-gui-related) elements of pndstore.
For many of these tests to work, libpnd.so.1 must be loadable.  Make sure it's
installed (ie: on a Pandora), or accessible by LD_LIBRARY_PATH."""
import unittest, shutil, os.path, locale, sqlite3, ctypes, shutil

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pndstore import options, database_update, packages, libpnd

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
        self.assertTrue(os.path.isdir(options.working_dir))


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
        # Should return list in desired order, always ending with en_US.
        # If no list is specified, should return (system lang, en_US).
        # If system has no default locale, it shouldn't appear in the list.
        l = locale.getdefaultlocale()[0]
        if l: locs = [l, 'en_US']
        else: locs = ['en_US']
        self.assertEquals(options.get_locale(), locs)

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
        "en_CA"
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

    def _check_entries(self, repo):
        with sqlite3.connect(options.get_database()) as db:
            db.row_factory = sqlite3.Row
            #Check that database has correct entries.
            c = db.execute('Select * From "%s"' % repo)
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
            self.assertEqual(i['categories'], "Game;Emulator")
            self.assertEqual(i['icon_cache'], None)
            i = c.fetchone()
            self.assertIsNone(i)


    def testUpdateRemote(self):
        database_update.update_remote()
        for r in options.get_repos():
            self._check_entries(r)
        # TODO: Test multiple different databases.
        # TODO: Test database updating (namely, removal of apps).


    def testBadRemote(self):
        with sqlite3.connect(options.get_database()) as db:
            c = db.cursor()
            #Test for a malformed JSON file.
            repo0 = os.path.join(options.get_working_dir(),
                os.path.basename(options.get_repos()[0]))
            with open(repo0, 'a') as r: r.write(',')
            self.assertRaises(ValueError, database_update.update_remote_url,
                database_update.open_repos()[0], c)
            #Test for incorrect version.
            with open(repo0, 'w') as r:
                r.write(self.repotxt % (os.path.basename(repo0), 99.7))
            self.assertRaises(database_update.RepoError,
                database_update.update_remote_url,
                database_update.open_repos()[0], c)

        database_update.update_remote()
        # Bad repo (first) must not exist.
        self.assertRaises(sqlite3.OperationalError, self._check_entries,
            options.get_repos()[0])
        # Good repo (second) should have correct entries.
        self._check_entries(options.get_repos()[1])

        #TODO: Test for missing fields, including missing languages.
        #TODO: Test for malformed fields: uri, icon, md5.


    def testMissingRemote(self):
        # Add extra non-existent URL to middle of config.
        with open(options.get_cfg()) as f:
            txt = f.read()
        new = txt.split('\n')
        new.insert(3, '"http://notreal.ihope",')
        with open(options.get_cfg(), 'w') as f:
            f.write('\n'.join(new))

        # Make sure other two still update correctly.
        database_update.update_remote()
        r = options.get_repos()
        self._check_entries(r[0])
        self.assertRaises(sqlite3.OperationalError, self._check_entries, r[1])
        self._check_entries(r[2])



    def testUpdateLocal(self):
        database_update.update_local()
        db = sqlite3.connect(options.get_database())
        db.row_factory = sqlite3.Row
        #Check that database has correct entries.
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
        self.assertEqual(i['categories'], "Game;ActionGame")
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
        self.assertEqual(i['categories'], "Game;ArcadeGame")
        c = db.execute('Select * From "%s" Where id="the-lonely-tower"'
            %database_update.LOCAL_TABLE)
        i = c.fetchone()
        self.assertEqual(i['id'], 'the-lonely-tower')
        self.assertEqual(i['version'], '2.2.0.0')
        self.assertEqual(i['author_name'], "Randy Heydon")
        self.assertEqual(i['author_website'],
            "http://randy.heydon.selfip.net/Programs/The Lonely Tower/")
        self.assertEqual(i['author_email'], None)
        self.assertEqual(i['title'], "The Lonely Tower")
        self.assertEqual(i['description'], "A dumb arty game made for a competition.")
        self.assertEqual(i['icon'],
            'lonelytower/assets/male-brunette-angry-listening-notrans.png')
        self.assertEqual(i['uri'], os.path.join(testfiles, 'The Lonely Tower-2.2.pnd'))
        self.assertEqual(i['md5'], '0314d0f7055052cd91ec608d63acad2a')
        self.assertEqual(i['vendor'], None)
        self.assertEqual(i['rating'], None)
        self.assertEqual(i['applications'], 'the-lonely-tower')
        self.assertEqual(i['previewpics'], None)
        self.assertEqual(i['licenses'], None)
        self.assertEqual(i['source'], None)
        self.assertEqual(i['categories'], "Game;RolePlaying")
        c = db.execute('Select * From "%s" Where id="sample-package"'
            %database_update.LOCAL_TABLE)
        i = c.fetchone()
        self.assertEqual(i['id'], 'sample-package')
        self.assertEqual(i['version'], '1.0.0.0')
        self.assertEqual(i['author_name'], "packagers name")
        self.assertEqual(i['author_website'], "http://www.website.foo")
        self.assertEqual(i['author_email'], "user@name.who")
        self.assertEqual(i['title'], "Sample Collection")
        self.assertEqual(i['description'],
            "This is a really verbose package with a whole lot of stuff from 2 different sources, mixing different things, having stuff in ways sometimes making use of stuff, often not.")
        self.assertEqual(i['icon'], "my-icon.png")
        self.assertEqual(i['uri'], os.path.join(testfiles, 'fulltest.pnd'))
        self.assertEqual(i['md5'], '201f7b98cc4933cd728087b548035b71')
        self.assertEqual(i['vendor'], None)
        self.assertEqual(i['rating'], None)
        self.assertEqual(i['applications'],
            'sample-app1;sample-app2;sample-app3')
        self.assertEqual(i['previewpics'],
            'preview-image.png;application_1.png;different-preview-image.png')
        # TODO: Add support for license reading, then enable these tests.
        #self.assertEqual(i['licenses'],
        #    'I do as I please;other;Qt-commercial;public domain;GPLv2+;GPLv2+')
        #self.assertEqual(i['source'],
        #    'git://git.openpandora.org;http://pandora.org/sources/package.tar.bz2')
        self.assertEqual(i['categories'],
            "Game;Emulator;System;Emulator;Game;StrategyGame;System")
        c = db.execute('Select * From "%s" Where id="chromium-dev"'
            %database_update.LOCAL_TABLE)
        i = c.fetchone()
        self.assertEqual(i['id'], 'chromium-dev')
        self.assertEqual(i['version'], '10.0.642.1')
        self.assertEqual(i['author_name'], "")
        self.assertEqual(i['author_website'], "http://sites.google.com/a/chromium.org/dev/")
        self.assertEqual(i['author_email'], None)
        self.assertEqual(i['title'], "Chromium-Dev")
        self.assertEqual(i['description'],
            u"Chromium is an open-source browser project that aims to build a safer, faster, and more stable way for all users to experience the web. This site contains design documents, architecture overviews, testing information, and more to help you learn to build and work with the Chromium source code.\u201d.")
        self.assertEqual(i['icon'], "product_logo_48.png")
        self.assertEqual(i['uri'], os.path.join(testfiles, 'Chromium-dev.pxml.pnd'))
        self.assertEqual(i['md5'], 'ec93f8e51b50be4ee51d87d342a6028a')
        self.assertEqual(i['vendor'], None)
        self.assertEqual(i['rating'], None)
        self.assertEqual(i['applications'], 'chromium-dev')
        self.assertEqual(i['previewpics'], './preview.jpg')
        self.assertEqual(i['licenses'], None)
        self.assertEqual(i['source'], None)
        self.assertEqual(i['categories'], 'Network;WebBrowser')
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
        # Note this gives the number of applications, not the number of
        # packages found.  This test has 4 packages, one of which holds 3 apps.
        n = libpnd.box_get_size(search)
        self.assertEqual(n, 10)

        node = libpnd.box_get_head(search)
        pnds = [libpnd.box_get_key(node)]
        for i in xrange(n-1):
            node = libpnd.box_get_next(node)
            pnds.append(libpnd.box_get_key(node))
        self.assertSetEqual(set(map(os.path.basename, pnds)), {'BubbMan2.pnd',
            'Sparks-0.4.2.pnd', 'The Lonely Tower-2.2.pnd', 'fulltest.pnd',
            'Chromium-dev.pxml.pnd', 'Hexen2.pxml.pnd', 'scummvm-op.pxml.pnd'})


    def testParsing(self):
        pxml = libpnd.pxml_get_by_path(
            os.path.join(testfiles, 'The Lonely Tower-2.2.pnd'))
        self.assertIsNotNone(pxml) # Check for failed parsing so we don't segfault.
        for app in pxml:
            if app is None: break
            self.assertEqual(libpnd.pxml_get_unique_id(app), 'the-lonely-tower')
            self.assertEqual(libpnd.pxml_get_app_name(app, 'en_US'), 'The Lonely Tower')
            libpnd.pxml_delete(app)


    def testAppdataPath(self):
        r_path = ctypes.create_string_buffer(256)

        ret = libpnd.get_appdata_path(
            '"%s"'%os.path.join(testfiles, 'The Lonely Tower-2.2.pnd'),
            'the-lonely-tower', r_path, 256)
        self.assertGreater(ret, 0)
        self.assertRegexpMatches(r_path.value, r'/pandora/appdata/the-lonely-tower/$')

        ret = libpnd.get_appdata_path(
            '"%s"'%os.path.join(testfiles, 'fulltest.pnd'),
            'sample-app3-appdata', r_path, 256)
        self.assertGreater(ret, 0)
        self.assertRegexpMatches(r_path.value, r'/pandora/appdata/sample-app3-appdata/$')

        # This test is noisy and prints stuff to stderr.  Just ignore it.
        ret = libpnd.get_appdata_path('"IGNORE ME"', 'somewhere', r_path, 256)
        self.assertEqual(ret, 0)


    def testAccruePXML(self):
        target = ctypes.create_string_buffer(libpnd.PXML_MAXLEN)

        # Find all PNDs for testing (as per testDiscovery).
        search = libpnd.disco_search(testfiles, None)
        n = libpnd.box_get_size(search)
        node = libpnd.box_get_head(search)
        pnds = [libpnd.box_get_key(node)]
        for i in xrange(n-1):
            node = libpnd.box_get_next(node)
            pnds.append(libpnd.box_get_key(node))

        # Accrue all their PXMLs.
        for pth in pnds:
            f = libpnd.libc.fopen(pth,'r')
            ret = libpnd.pnd_seek_pxml(f)
            self.assertEqual(ret, 1)

            ret = libpnd.pnd_accrue_pxml(f, target, libpnd.PXML_MAXLEN)
            self.assertEqual(ret, 1)
            self.assertIn(target.value, open(pth,'rb').read())
            self.assertEqual(target.value[:5], '<PXML')
            # Some PNDs seem to have the first 6 bytes of the icon added on to
            # the end of the accrued PXML.  Hopefully won't disrupt parsing.
            self.assertIn('</PXML>', target.value[-13:])


    def testParsing(self):
        pxml = libpnd.pxml_get_by_path(
            os.path.join(testfiles, 'The Lonely Tower-2.2.pnd'))
        self.assertIsNotNone(pxml) # Check for failed parsing so we don't segfault.
        for app in pxml:
            if app is None: break
            self.assertEqual(libpnd.pxml_get_unique_id(app), 'the-lonely-tower')
            self.assertEqual(libpnd.pxml_get_app_name(app, 'en_US'), 'The Lonely Tower')
            libpnd.pxml_delete(app)



class TestPackages(unittest.TestCase):
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
        v = packages.PNDVersion
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
        self.assertEquals(packages.get_remote_tables(), options.get_repos())


    def testPackageInstance(self):
        p = packages.PackageInstance(database_update.LOCAL_TABLE, 'bubbman2')
        self.assertGreater(p.version, '1.0.3.0')


    def testPackage(self):
        p = packages.Package('bubbman2')


    def testPackageGetLatest(self):
        p = packages.Package('sparks')
        self.assertIs(p.local, p.get_latest())
        p = packages.Package('the-lonely-tower')
        self.assertIs(p.local, p.get_latest())
        p = packages.Package('bubbman2')
        self.assertIsNot(p.local, p.get_latest())
        self.assertEqual(p.get_latest().version, '1.0.4.0')


    def testGetAll(self):
        ps = packages.get_all()
        for p in ps:
            self.assertIsInstance(p, packages.Package)
        # TODO: Some better tests for this function.
        # 28 in repo.json, 7 local, 2 in both.
        self.assertEqual(len(ps), 28 + 7 - 2)


    def testGetAllLocal(self):
        ps = packages.get_all_local()
        for p in ps:
            self.assertIsInstance(p, packages.Package)
        # TODO: Some better tests for this function.
        self.assertEqual(len(ps), 7)


    def testGetUpdates(self):
        ps = packages.get_updates()
        self.assertEqual(len(ps), 1)
        self.assertEqual(ps[0].id, 'bubbman2')


    def testRemove(self):
        # Create a slightly-modified sacrificial file.
        src = open(os.path.join(testfiles, 'fulltest.pnd')).read()
        dstpath = os.path.join(testfiles, 'fulltest2.pnd')
        with open(dstpath,'w') as dst:
            dst.write(src.replace('sample-package', 'sample2', 1))
        # Make sure it gets in the database.
        database_update.update_local()
        with sqlite3.connect(options.get_database()) as db:
            self.assertIsNotNone( db.execute(
                'Select * From "%s" Where id="sample2"'
                % database_update.LOCAL_TABLE).fetchone() )
        # Now remove it!
        p = packages.Package('sample2')
        p.remove()
        # And make sure it's gone.
        self.assertFalse(os.path.exists(dstpath))
        with sqlite3.connect(options.get_database()) as db:
            self.assertIsNone( db.execute(
                'Select * From "%s" Where id="sample2"'
                % database_update.LOCAL_TABLE).fetchone() )
        self.assertFalse(p.local.exists)


    def testMissingTables(self):
        os.remove(options.get_database())
        p = packages.Package('not-even-real')
        self.assertFalse(p.local.exists)
        self.assertItemsEqual(p.remote, [])

        database_update.update_local()
        p = packages.Package('not-even-real')
        self.assertFalse(p.local.exists)
        self.assertItemsEqual(p.remote, [])

        with sqlite3.connect(options.get_database()) as db:
            db.execute("""Create Table "%s" (
                url Text Primary Key, name Text, etag Text, last_modified Text
                )""" % database_update.REPO_INDEX_TABLE)
        p = packages.Package('not-even-real')
        self.assertFalse(p.local.exists)
        self.assertItemsEqual(p.remote, [])



class TestFileOperations(unittest.TestCase):
    pass




if __name__=='__main__':
    unittest.main()
