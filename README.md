# deluge-extractor
Plugin for the [deluge](http://deluge-torrent.org/) *V2* torrent client that extracts compressed files upon torrent completion.

This is a modified version of the "Extractor" plugin, with the added option to extract in place.

This is updated to work on Deluge V2. I'm not sure if it'll work with V1 versions...you tell me. I think it should.0

* Target folder for extracting the torrent can be specified
* A sub folder (name of torrent) can be created within the target folder
* In-place extraction of the torrent in the torrent's download folder is possible as well

# Features
Optional download locations:
* In-place: Extract each .rar file to it's exact location. If a file is in /downloads/TORRENTNAME/subs/subs.rar, it will be extracted to /downloads/TORRENTNAME/subs/.
* Torrent root: Extract each rar to the root of the torrent download. If a file is in /downloads/TORRENTNAME/sub/subs.rar, it will be extracted to /downloads/TORRENTNAME/.
* Selected Folder: Extract to a directory that you specify.

Label filtering:
Enter a comma-separated list of labels, only those labels will be extracted. Works with the default labels plugin, as well as labelplus.

## Has been tested on:

* Deluge 2.0.5


## Supported File formats:

UniX-ish supports:
* .rar, .tar, .zip, .7z .tar.gz, .tgz, .tar.bz2, .tbz .tar.lzma, .tlz, .tar.xz, .txz

Windows supports:
* .rar, .zip, .tar, .7z, .xz, .lzma

( Requires [7-zip]( http://www.7-zip.org/) to be installed on the system running the client resp. the daemon if run in daemon mode )


# Build Instructions
To build the python egg file:
```
  python setup.py bdist_egg
```

# Installation Instructions

Download the [egg file](https://github.com/cvarta/deluge-extractor/releases/download/v.0.4.1/SimpleExtractor-0.4.1-py2.7.egg) of the plugin.

#### Notes
* Plugin eggs have the Python version encoded in the filename and will only load in Deluge if the versions match. (e.g. Plugin-1.0-py2.7.egg is a Python 2.7 egg.)

* On *nix systems, you can verify Python version with: ```python --version```

* The bundled Python version for Windows executable is 2.6 and for MacOSX Deluge.app it is 2.7.

* If a plugin does not have a Python version available it is usually possible to rename it to match your installed version (e.g. Plugin-1.0-py2.6.egg to Plugin-1.0-py2.7.egg) and it will still run normally

### GUI-Install:

Preferences -> Plugins -> Install plugin

Locate the downloaded egg file and select it.

### Manual Install:

Copy the egg file into the ```plugins``` directory in Deluge config:

Linux/*nix:

``` ~/.config/deluge/plugins ```

Windows:

``` %APPDATA%\deluge\plugins ```

### Client-Server Setups:

When running the Deluge daemon, ``` deluged ``` and the Deluge client on separate computers, the plugin must be installed on both of them. When installing the egg through the GTK client it will be placed in the plugins directory of your computer, as well as copied over to the computer running the daemon.

#### Note: If the Python versions on the server and desktop computer do not match, you will have to copy the egg file to the server manually.

For example in the setup below you will have to install the py2.6 egg on the desktop as you normal would do but then manually install the py2.7 egg onto the server.

* Windows desktop with Python 2.6 running GTK client.
* Linux server with Python 2.7 running deluged

#### Note: The Windows installer comes bundled with python: either python 2.6 or 2.7 depending on the intstaller you used.


### Support my work?

If you dig this plugin and want to say thanks, the best way to do it is by sending a paypal donation to donate.to.digitalhigh@gmail.com

All donations are appreciated...but none are required :D
