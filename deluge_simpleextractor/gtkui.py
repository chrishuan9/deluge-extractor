# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Andrew Resch <andrewresch@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2019-2020 Digitalhigh <donate.to.digitalhigh@gmail.com>
#
#

from __future__ import unicode_literals

import logging

import gi  # isort:skip (Required before Gtk import).

gi.require_version('Gtk', '3.0')  # NOQA: E402

# isort:imports-thirdparty
from gi.repository import Gtk

# isort:imports-firstparty
import deluge.component as component
from deluge.plugins.pluginbase import Gtk3PluginBase
from deluge.ui.client import client

# isort:imports-localfolder
from .common import get_resource

log = logging.getLogger(__name__)


class GtkUI(Gtk3PluginBase):
    def enable(self):
        self.plugin = component.get('PluginManager')
        self.builder = Gtk.Builder()
        self.builder.add_from_file(get_resource('simpleextractor_prefs.ui'))

        component.get('Preferences').add_page(
            _('Simple Extractor'), self.builder.get_object('extractor_prefs_box')
        )
        
        self.plugin.register_hook('on_apply_prefs', self.on_apply_prefs)
        self.plugin.register_hook('on_show_prefs', self.on_show_prefs)
        self.on_show_prefs()

    def disable(self):
        component.get('Preferences').remove_page(_('Simple Extractor'))
        self.plugin.deregister_hook(
            'on_apply_prefs', self.on_apply_prefs
        )
        self.plugin.deregister_hook(
            'on_show_prefs', self.on_show_prefs
        )
        del self.builder

    def on_apply_prefs(self):
        log.debug('applying prefs for Simple Extractor')
        if client.is_localhost():
            path = self.builder.get_object('folderchooser_path').get_filename()
        else:
            path = self.builder.get_object('extract_path').get_text()

        config = {
            'extract_path': path,
            'extract_selected_folder': self.builder.get_object("extract_selected_folder").get_active(),
            'extract_in_place': self.builder.get_object("extract_in_place").get_active(),
            'extract_torrent_root': self.builder.get_object("extract_torrent_root").get_active(),
            'label_filter': self.builder.get_object("label_filter").get_text()
        }

        client.simpleextractor.set_config(config)

    def on_show_prefs(self):
        def on_get_config(config):
            if client.is_localhost():
                self.builder.get_object('folderchooser_path').set_current_folder(config['extract_path'])
                self.builder.get_object('folderchooser_path').show()
                self.builder.get_object('extract_path').hide()
            else:
                self.builder.get_object('extract_path').set_text(config['extract_path'])
                self.builder.get_object('folderchooser_path').hide()
                self.builder.get_object('extract_path').show()

            self.builder.get_object('extract_selected_folder').set_active(
                config['extract_selected_folder']
            )
            self.builder.get_object('extract_torrent_root').set_active(
                config['extract_torrent_root']
            )
            self.builder.get_object('extract_in_place').set_active(
                config['extract_in_place']
            )
            self.builder.get_object('label_filter').set_text(config['label_filter'])

        client.simpleextractor.get_config().addCallback(on_get_config)
