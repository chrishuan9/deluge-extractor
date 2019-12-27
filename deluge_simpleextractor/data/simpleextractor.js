/*!
 * simpleextractor.js
 *
 * Copyright (c) Damien Churchill 2010 <damoxc@gmail.com>
 * Copyright (C) Digitalhigh 2019 <donate.to.digitalhigh@gmail.com>
 *
 *
 */

Ext.ns('Deluge.ux.preferences');

/**
 * @class Deluge.ux.preferences.SimpleExtractorPage
 * @extends Ext.Panel
 */
Deluge.ux.preferences.SimpleExtractorPage = Ext.extend(Ext.Panel, {

    title: _('SimpleExtractor'),
    layout: 'fit',
    border: false,

    initComponent: function() {
        Deluge.ux.preferences.SimpleExtractorPage.superclass.initComponent.call(this);

        this.form = this.add({
            xtype: 'form',
            layout: 'form',
            border: false,
            autoHeight: true
        });


        this.behaviorSet = this.form.add({
            xtype: 'fieldset',
            border: false,
            title: '',
            autoHeight: true,
            labelAlign: 'top',
            labelWidth: 80,
            defaultType: 'textfield'
        });

        this.behaviorSet.add({
             xtype: 'label',
            fieldLabel: _('<b>Extract Behavior:</b></br>'),
            labelSeparator : '',
            name: '',
            width: '97%'
        });

        // Behavior Label

        // Add radio group for extract behavior
        this.extractBehavior = this.behaviorSet.add({
            xtype: 'radiogroup',
            columns: 1,
            colspan: 2,
            style: 'margin-left: 10px',
            items: [
                {
                    boxLabel: _('Selected Folder'),
                    name: 'extract_behavior',
                    inputValue: "extract_selected_folder"
                },
                {
                    boxLabel: _('Torrent Root'),
                    name: 'extract_behavior',
                    inputValue: "extract_torrent_root"
                },
                {
                    boxLabel: _('In-Place'),
                    name: 'extract_behavior',
                    inputValue: "extract_in_place"
                }
            ],
        });

        this.destinationSet = this.form.add({
            xtype: 'fieldset',
            border: false,
            title: '',
            autoHeight: true,
            labelAlign: 'top',
            labelWidth: 80,
            defaultType: 'textfield'
        });

        // Destination label
        this.extractPath = this.destinationSet.add({
            fieldLabel: _('<b>Destination:</b></br>'),
            name: 'extract_path',
            labelSeparator : '',
            width: '97%'
        });


        this.labelSet = this.form.add({
            xtype: 'fieldset',
            border: false,
            title: '',
            autoHeight: true,
            labelAlign: 'top',
            labelWidth: 80,
            defaultType: 'textfield'
        });

        // Label Filter Label
        this.labelFilter = this.labelSet.add({
            fieldLabel: _('<b>Label Filtering:</b></br>'),
            name: 'label_filter',
            labelSeparator : '',
            width: '97%'
        });

         this.labelSet.add({
             xtype: 'label',
            fieldLabel: _('</br>Comma-separated, leave blank for none.'),
            labelSeparator : '',
            name: '',
            width: '97%'
        });





        this.on('show', this.updateConfig, this);
    },

    onApply: function() {
        // build settings object
        var config = {};
        config['extract_path'] = this.extractPath.getValue();
        var eBehavior = this.extractBehavior.getValue();
        config['extract_in_place'] = false;
        config['extract_torrent_root'] = false;
        config['extract_selected_folder'] = false;
        config[eBehavior] = true;
        config['label_filter'] = this.labelFilter.getValue();

        deluge.client.simpleextractor.set_config(config);
    },

    onOk: function() {
        this.onApply();
    },

    updateConfig: function() {
        deluge.client.simpleextractor.get_config({
            success: function(config) {
                this.extractPath.setValue(config['extract_path']);
                var behavior = "extract_selected_folder";
                if (config['extract_in_place']) {
                    behavior = 'extract_in_place';
                }
                if (config['extract_torrent_root']) {
                    behavior = 'extract_torrent_root';
                }
                this.extractBehavior.setValue(behavior);
                this.labelFilter.setValue(config['label_filter']);
            },
            scope: this
        });
    }
});


Deluge.plugins.SimpleExtractorPlugin = Ext.extend(Deluge.Plugin, {
    name: 'SimpleExtractor',
    onDisable: function() {
        deluge.preferences.removePage(this.prefsPage);
    },

    onEnable: function() {
        this.prefsPage = deluge.preferences.addPage(new Deluge.ux.preferences.SimpleExtractorPage());
    }
});
Deluge.registerPlugin('SimpleExtractor', Deluge.plugins.SimpleExtractorPlugin);
