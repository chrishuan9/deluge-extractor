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
import subprocess
import traceback
from shutil import which

import deluge.component as component
import deluge.configmanager
from deluge.common import windows_check
from deluge.configmanager import ConfigManager
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
        'C:\\Program Files (x86)\\7-Zip\\7z.exe'
    ]

    # Future support:
    # 7-zip cannot extract tar.* with single command.
    #    ".tar.bz2", ".tbz",
    #    ".tar.lzma", ".tlz",
    #    ".tar.xz", ".txz",
    # BUT - Windows 10 can...see below
    exts_7z = ['.rar', '.zip', '.tar', '.7z', '.xz', '.lzma']
    for win_7z_exe in win_7z_exes:
        if which(win_7z_exe):
            EXTRACT_COMMANDS = {
                '.r00': [win_7z_exe, 'x', '-y'],
                '.rar': [win_7z_exe, 'x', '-y'],
                '.zip': [win_7z_exe, 'x', '-y'],
                '.tar': [win_7z_exe, 'x', '-y'],
                '.7z': [win_7z_exe, 'x', '-y'],
                '.xz': [win_7z_exe, 'x', '-y'],
                '.lzma': [win_7z_exe, 'x', '-y']
            }
            break
    # Windows 10 build 17063 added the 'nix Tar command, so let's support it. (No xz/bz2/lzma yet)
    if which('tar'):
        log.info("Windows has TAR support, adding commands.")
        EXTRACT_COMMANDS['.tar'] = ['tar', '-xf'],
        EXTRACT_COMMANDS['.tar.gz'] = ['tar', '-xzf'],
        EXTRACT_COMMANDS['.tgz'] = ['tar', '-xzf']

else:
    required_cmds = ['unrar', 'unzip', 'tar', '7zr']

    EXTRACT_COMMANDS = {
        '.rar': ['unrar', 'x', '-o+', '-y'],
        '.r00': ['unrar', 'x', '-o+', '-y'],
        '.tar': ['tar', '-xf'],
        '.zip': ['unzip'],
        '.tar.gz': ['tar', '-xzf'],
        '.tgz': ['tar', '-xzf'],
        '.tar.bz2': ['tar', '-xjf'],
        '.tbz': ['tar', '-xjf'],
        '.tar.lzma': ['tar', '--lzma', '-xf'],
        '.tlz': ['tar', '--lzma', '-xf'],
        '.tar.xz': ['tar', '-Jf'],
        '.txz': ['tar', '--xJf'],
        '.7z': ['7zr', 'x']
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
        if filters != "" and len(labels) > 0:
            log.info("Saved filters:", filters)
            # Make the label list once, save needless processing.
            if "," in self.config['label_filter']:
                log.info("we have a list.")
                label_list = filters.split(",")
            else:
                label_list = [filters]
            # Make sure there's actually a label
            for label in labels:
                log.info("Label for torrent is %s", label)
                # Check if it's more than one, split
                for check in label_list:
                    print("Comparing %s to %s.", label, check)
                    if check.strip() == label:
                        log.info("This matches, we should extract it.")
                        do_extract = True
                        break
                # We don't need to keep checking labels if we've found a match
                if do_extract:
                    break
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
                log.debug("Handling file %s", f['path'])
                file_root, file_ext = os.path.splitext(f['path'])
                file_ext_sec = os.path.splitext(file_root)[1]
                if file_ext_sec == ".tar":
                    file_ext = file_ext_sec + file_ext
                    file_root = os.path.splitext(file_root)[0]
                # IF it's not extractable, move on.
                if file_ext not in EXTRACT_COMMANDS:
                    continue

                # Check to prevent double extraction with rar/r00 files
                if file_ext == '.r00' and any(x['path'] == file_root + '.rar' for x in files):
                    log.debug('Skipping file with .r00 extension because a matching .rar file exists: %s', f['path'])
                    continue

                # Check for RAR archives with PART in the name
                if file_ext == '.rar' and 'part' in file_root:
                    part_num = file_root.split('part')[1]
                    if part_num.isdigit() and int(part_num) != 1:
                        log.debug('Skipping remaining multi-part rar files: %s', f['path'])
                        continue

                log.info("Extracting %s", f)
                fpath = os.path.normpath(os.path.join(t_status['download_location'], f['path']))

                # Get the destination path, use that by default
                dest = os.path.normpath(self.config["extract_path"])

                # Override destination if extract_torrent_root is set
                if extract_torrent_root:
                    dest = os.path.join(os.path.normpath(t_status['download_location']), t_status['name'])

                # Override destination to file path if in_place set
                f_parent = os.path.normpath(os.path.join(t_status['download_location'], os.path.dirname(f['path'])))
                if extract_in_place and ((not os.path.exists(f_parent)) or os.path.isdir(f_parent)):
                    dest = f_parent
                    log.debug("Extracting in-place: %S", dest)

                try:
                    os.makedirs(dest)
                except OSError as ex:
                    if not (ex.errno == errno.EEXIST and os.path.isdir(dest)):
                        log.error("Error creating destination folder: %s", ex)
                        break

                # Lookup command array
                cmd = EXTRACT_COMMANDS[file_ext]
                # Append file path
                cmd.append(fpath)

                # Do it!
                try:
                    log.debug('Extracting with command: "%s" from working dir "%s"', " ".join(cmd), str(dest))
                    process = subprocess.run(cmd, cwd=dest, capture_output=True)

                    if process.returncode == 0:
                        log.info('Extract successful!')
                    else:
                        log.error(
                            'Extract failed: %s with code %s', fpath, process.returncode
                        )
                except Exception as ex:
                    log.error("Exception:", traceback.format_exc())

                # Don't mark an extracting torrent complete until callback is fired.
                tid.is_finished = True
                log.info("Torrent extraction/handling complete.")

        else:
            tid.is_finished = True
            log.info("Torrent extraction/handling complete.")

    @staticmethod
    def get_labels(torrent_id):
        """
         Asking the system about the labels isn't very cool, so try this instead
        """
        labels = []
        label_config = ConfigManager('label.conf', defaults=False)
        if 'torrent_labels' in label_config:
            log.debug("We have a Label config.")
            if torrent_id in label_config['torrent_labels']:
                labels.append(label_config['torrent_labels'][torrent_id])

        label_plus_config = ConfigManager('labelplus.conf', defaults=False)
        if 'mappings' in label_plus_config:
            log.debug("We have a label plus config.")
            if torrent_id in label_plus_config['mappings']:
                mapping = label_plus_config['mappings'][torrent_id]
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