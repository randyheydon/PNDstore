========
PNDstore
========
    Install and update PNDs on your Pandora

This application is designed to allow for the installation and updating of `PND files`_ on the `Pandora handheld`_.  It can interface with any site that implements the `PND repository specification`_ to do so.


Limitations
===========
On package removal, appdata directories and override files are left in place.  These need to be manually removed if desired.

On package upgrade, the new version of the package will be installed with a filename dictated by the repository from which the package has been downloaded.  Therefore, any manual renaming will be lost, and any override files will need to be manually renamed to match.

If multiple packages with the same ID are present on the system's searchpath, only one will be detected.  Which is detected is undefined.


Acknowledgements
================
Many thanks to the people who helped make this possible, particularly skeezix for libpnd and milkshake for creating a repository that gives this a reason to exist.

Many more thanks to the multitude of people who test and give feedback on this, without whom this wouldn't even run.

The contents of test/testdata come from a variety of sources:
* "apps", "desktop", and "mmenu.conf" are from libpnd, by skeezix, and is licensed under the LGPL.  See http://git.openpandora.org/cgi-bin/gitweb.cgi?p=pandora-libraries.git
* "fulltest.pnd" is a minor modification of "full-sample_PXML.xml", also from libpnd, also under the LGPL, but created by Ivanovic.
* "BubbMan2.pnd" is by pymike, and is licensed under the LGPL.  See http://www.pygame.org/project-BubbMan+2-1114-.html
* "Sparks-0.4.2.pnd" is by haltux, and is licensed under the GPL. See https://github.com/haltux/Sparks
* "The Lonely Tower-2.2.pnd" is by the author, and is licensed under CC-BY-SA 3.0.  See http://randy.heydon.selfip.net/Programs/The%20Lonely%20Tower/
* All other "*.pxml.pnd" files are PXML metadata extracted from their respective packages.  You should be able to find links to the original packages on http://pandorawiki.org

The icon used here (resources/icon.png) is the system-software-update icon from the GNOME icon theme, and is licensed under the GPL.

The screenshot included here (resources/screen1.png) was kindly provided by thatgui of the Pandora forums at http://boards.openpandora.org

.. _PND files: http://pandorawiki.org/PND
.. _Pandora handheld: http://openpandora.org
.. _PND repository specification: http://pandorawiki.org/PND_repository_specification
