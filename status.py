#!/usr/bin/python3
###############################################################################
# status.py - python i3bar status line generator
#
# author: mutantmonkey <mutantmonkey@mutantmonkey.in>
###############################################################################

import importlib
import json
import os.path
import subprocess
import sys
import time
import widgets
import yaml


def load_config(configpath):
    config = yaml.safe_load(open(configpath))

    if 'interval' in config:
        config['interval'] = int(config['interval'])
    else:
        config['interval'] = 2

    if 'netctl_check_interval' in config:
        config['netctl_check_interval'] = int(config['netctl_check_interval'])
    else:
        config['netctl_check_interval'] = 30

    return config


def get_widgets(config):
    if 'widgets_netctl' in config:
        profile = None
        out = subprocess.check_output(['netctl', 'list']).decode('utf-8')
        for line in out.splitlines():
            if line[0:2] == '* ':
                profile = line[2:]
                break

        if profile in config['widgets_netctl']:
            return load_widgets(config['widgets_netctl'][profile])

    return load_widgets(config['widgets'])


def load_widgets(cwidgets):
    widgets = []
    for item in cwidgets:
        if isinstance(item, dict):
            # grab the first dict from the list of widgets
            components, args = item.copy().popitem()
        else:
            # if the item is not a dict, then it is a widget with no args
            # for backwards compatibility, we split on spaces
            splat = item.split(' ')
            components = splat[0]
            if len(splat) > 1:
                args = splat[1:]
            else:
                args = []

        components = components.split('.')
        path = '.'.join(components[:-1])
        module = importlib.import_module(path)

        class_ = getattr(module, components[-1])

        if isinstance(args, dict):
            # keyword arguments
            instance = class_(**args)
        elif isinstance(args, list):
            # positional arguments
            instance = class_(*args)
        else:
            # single argument
            instance = class_(args)

        widgets.append(instance)

    return widgets


def theme_widget(wout, iconpath):
    widget_cfg = config['theme'][wout['name']]

    wout['icon'] = ""
    if 'icon' in widget_cfg:
        widget_icons = widget_cfg['icon'].split()
        if len(widget_icons) > 2 and '_status' in wout:
            if wout['_status'] == 'error':
                icon = widget_icons[2]
            elif wout['_status'] == 'warn':
                icon = widget_icons[1]
            else:
                icon = widget_icons[0]
        else:
            icon = widget_icons[0]

        if icon[0:2] == 'U+':
            icon = chr(int(icon[2:], 16))
            wout['full_text'] = icon + '  ' + wout['full_text']
        else:
            wout['icon'] = os.path.join(iconpath, 'icons', icon)
            wout['full_text'] = ' ' + wout['full_text']

    if 'color' in widget_cfg:
        widget_colors = widget_cfg['color'].split()
        if len(widget_colors) > 2 and '_status' in wout:
            if wout['_status'] == 'error':
                wout['color'] = widget_colors[2]
            elif wout['_status'] == 'warn':
                wout['color'] = widget_colors[1]
            else:
                wout['color'] = widget_colors[0]
        else:
            wout['color'] = widget_colors[0]

    return wout


if __name__ == '__main__':
    if len(sys.argv) > 1:
        configpath = sys.argv[1]
    else:
        try:
            import xdg.BaseDirectory
            configpath = xdg.BaseDirectory.load_first_config('mmbar/config.yml')
        except:
            configpath = os.path.expanduser('~/.config/mmbar/config.yml')

    iconpath = os.path.dirname(os.path.abspath(__file__))
    config = load_config(configpath)
    widgets = get_widgets(config)
    i = 0

    print(json.dumps({'version': 1}) + '[[]')
    while True:
        if i >= config['netctl_check_interval']:
            widgets = get_widgets(config)
            i = 0

        output = []
        for widget in widgets:
            wout = widget.output()

            if wout is not None:
                if wout['name'] in config['theme']:
                    wout = theme_widget(wout, iconpath)
                output.append(wout)
        print(',' + json.dumps(output), flush=True)

        i += config['interval']
        time.sleep(config['interval'])
    print(']')
