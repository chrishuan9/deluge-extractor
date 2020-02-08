# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Andrew Resch <andrewresch@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
#
# This file is part of Deluge and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

from __future__ import unicode_literals

import errno
import logging
import os

from twisted.internet.utils import getProcessOutputAndValue
from twisted.python.procutils import which

import deluge.component as component
import deluge.configmanager
from deluge.configmanager import ConfigManager
from deluge.common import windows_check
from deluge.core.rpcserver import export
from deluge.plugins.pluginbase import CorePluginBase

log = logging.getLogger(__name__)

DEFAULT_PREFS = {'extract_path': '',
                 'extract_in_place': False,
                 'extract_selected_folder': False,
                 'extract_torrent_root': True,
                 'label_filter': ''}

if windows_check():
    win_7z_exes = [
        '7z.exe',
        'C:\\Program Files\\7-Zip\\7z.exe',
        'C:\\Program Files (x86)\\7-Zip\\7z.exe',
    ]

    switch_7z = 'x -y'
    # Future suport:
    # 7-zip cannot extract tar.* with single command.
    #    ".tar.gz", ".tgz",
    #    ".tar.bz2", ".tbz",
    #    ".tar.lzma", ".tlz",
    #    ".tar.xz", ".txz",
    exts_7z = ['.rar', '.zip', '.tar', '.7z', '.xz', '.lzma']
    for win_7z_exe in win_7z_exes:
        if which(win_7z_exe):
            EXTRACT_COMMANDS = dict.fromkeys(exts_7z, [win_7z_exe, switch_7z])
            break
else:
    required_cmds = ['unrar', 'unzip', 'tar', 'unxz', 'unlzma', '7zr', 'bunzip2']
    # Possible future suport:
    # gunzip: gz (cmd will delete original archive)
    # the following do not extract to dest dir
    # ".xz": ["xz", "-d --keep"],
    # ".lzma": ["xz", "-d --format=lzma --keep"],
    # ".bz2": ["bzip2", "-d --keep"],

    EXTRACT_COMMANDS = {
        '.rar': ['unrar', 'x -o+ -y'],
        '.tar': ['tar', '-xf'],
        '.zip': ['unzip', ''],
        '.tar.gz': ['tar', '-xzf'],
        '.tgz': ['tar', '-xzf'],
        '.tar.bz2': ['tar', '-xjf'],
        '.tbz': ['tar', '-xjf'],
        '.tar.lzma': ['tar', '--lzma -xf'],
        '.tlz': ['tar', '--lzma -xf'],
        '.tar.xz': ['tar', '--xz -xf'],
        '.txz': ['tar', '--xz -xf'],
        '.7z': ['7zr', 'x'],
    }
    # Test command exists and if not, remove.
    for command in required_cmds:
        if not which(command):
            for k, v in list(EXTRACT_COMMANDS.items()):
                if command in v[0]:
                    log.warning('%s not found, disabling support for %s', command, k)
                    del EXTRACT_COMMANDS[k]

if not EXTRACT_COMMANDS:
    raise Exception('No archive extracting programs found, plugin will be disabled')


class Core(CorePluginBase):
    def enable(self):
        self.config = deluge.configmanager.ConfigManager(
            'simpleextractor.conf', DEFAULT_PREFS
        )
        if not self.config['extract_path']:
            self.config['extract_path'] = deluge.configmanager.ConfigManager(
                'core.conf'
            )['download_location']
        component.get('EventManager').register_event_handler(
            'TorrentFinishedEvent', self._on_torrent_finished
        )

    def disable(self):
        component.get('EventManager').deregister_event_handler(
            'TorrentFinishedEvent', self._on_torrent_finished
        )

    def update(self):
        pass

    def _on_torrent_finished(self, torrent_id):
        """
        This is called when a torrent finishes and checks if any files to extract.
        """
        tid = component.get('TorrentManager').torrents[torrent_id]
        t_status = tid.get_status([], False, False, True)
        do_extract = False
        tid.is_finished = False
        log.info("Processing completed torrent %s", t_status)
        # Fetch our torrent's label
        labels = self.get_labels(torrent_id)
        log.info("Labels collected: %s", labels)
        # If we've set a label filter, process it
        filters = self.config['label_filter']
        log.info("Saved filters:", filters)
        if filters is not "":
            # Make sure there's actually a label
            if len(labels) > 0:
                for label in labels:
                    log.info("Label for torrent is %s", label)
                    # Check if it's more than one, split
                    if "," in self.config['label_filter']:
                        log.info("And we have a list")
                        label_list = filters.split(",")
                        # And loop
                        for check in label_list:
                            print("Comparing " + label + " to " + check)
                            if check.strip() == label:
                                log.info("This matches, we should extract it.")
                                do_extract = True
                                break
                    # Otherwise, just check the whole string
                    else:
                        log.info("Single label string detected: ", filters)
                        if filters.strip() == label:
                            log.info("This matches, we should extract it.")
                            do_extract = True
            # We don't need to do this, but it adds sanity
            else:
                log.info("We have a label filter and no label, doing nothing")
                do_extract = False
        # Otherwise, we just extract everything
        else:
            log.info("No label, extracting.")
            do_extract = True

        # Now, extract if filter match or no filter set
        extract_in_place = self.config["extract_in_place"]
        extract_torrent_root = self.config["extract_torrent_root"]

        if do_extract:
            files = tid.get_files()
            for f in files:
                log.info("Handling file %s", f['path'])
                f_parent = os.path.dirname(f['path'])
                file_root, file_ext = os.path.splitext(f['path'])
                file_ext_sec = os.path.splitext(file_root)[1]
                if file_ext_sec and file_ext_sec + file_ext in EXTRACT_COMMANDS:
                    log.info("We should extract this.")
                    file_ext = file_ext_sec + file_ext
                elif file_ext not in EXTRACT_COMMANDS or file_ext_sec == '.tar':
                    log.info('Cannot extract file with unknown file type: %s', f['path'])
                    continue
                elif file_ext == '.rar' and 'part' in file_ext_sec:
                    part_num = file_ext_sec.split('part')[1]
                    if part_num.isdigit() and int(part_num) != 1:
                        log.info('Skipping remaining multi-part rar files: %s', f['path'])
                        continue

                cmd = EXTRACT_COMMANDS[file_ext]

                fpath = os.path.join(
                    t_status['download_location'], os.path.normpath(f['path'])
                )

                # Get the destination path, use that by default
                dest = os.path.normpath(self.config["extract_path"])
                name_dest = os.path.join(dest, t_status["name"])

                # Override destination if extract_torrent_root is set
                if extract_torrent_root:
                    dest = name_dest

                # Override destination to file path if in_place set
                if extract_in_place and ((not os.path.exists(f_parent)) or os.path.isdir(f_parent)):
                    dest = f_parent
                    log.debug("Extracting in-place: " + dest)

                try:
                    os.makedirs(dest)
                except OSError as ex:
                    if not (ex.errno == errno.EEXIST and os.path.isdir(dest)):
                        log.error("EXTRACTOR: Error creating destination folder: %s", ex)
                        break

                def on_extract(result, torrent_id, fpath):
                    # Check command exit code.
                    if not result[2]:
                        log.info('Extract successful: %s (%s)', fpath, torrent_id)
                    else:
                        log.error(
                            'Extract failed: %s (%s) %s', fpath, torrent_id, result[1]
                        )

                # Run the command and add callback.
                log.info(
                    'Extracting %s from %s with %s %s to %s',
                    fpath,
                    torrent_id,
                    cmd[0],
                    cmd[1],
                    dest,
                )
                d = getProcessOutputAndValue(
                    cmd[0], cmd[1].split() + [str(fpath)], os.environ, str(dest)
                )
                d.addCallback(on_extract, torrent_id, fpath)

        tid.is_finished = True
        log.info("Torrent extraction/handling complete.")

    def get_labels(self, torrent_id):
        """
         Asking the system about the labels isn't very cool, so try this instead
        """
        labels = []
        label_config = ConfigManager('label.conf', defaults=False)
        if label_config is not False:
            log.info("We have a Label config")
            if 'torrent_labels' in label_config:
                if torrent_id in label_config['torrent_labels']:
                    log.info("Data from Label plugin: %s", label_config['torrent_labels'][torrent_id])
                    labels.append(label_config['torrent_labels'][torrent_id])

        label_plus_config = ConfigManager('labelplus.conf', defaults=False)
        if label_plus_config is not False:
            log.info("We have a label plus config")
            if 'mappings' in label_plus_config:
                if torrent_id in label_plus_config['mappings']:
                    mapping = label_plus_config['mappings'][torrent_id]
                    log.info("We have a label plus mapping: %s", mapping)
                    labels.append(label_plus_config['labels'][mapping]['name'])
        return labels

    @export
    def set_config(self, config):
        """Sets the config dictionary."""
        for key in config:
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary."""
        return self.config.config
