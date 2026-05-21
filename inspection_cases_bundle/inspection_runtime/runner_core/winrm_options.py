#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def get_winrm_shell(mod):
    shell = getattr(mod, 'WINRM_SHELL', None)
    if shell is None and hasattr(mod, 'CHECK_CLASS'):
        shell = getattr(mod.CHECK_CLASS, 'WINRM_SHELL', None)
    return shell


def build_winrm_options(mod, winrm_options):
    wr_opts = dict(winrm_options)
    shell = get_winrm_shell(mod)
    if shell:
        wr_opts['shell'] = shell
    return wr_opts
