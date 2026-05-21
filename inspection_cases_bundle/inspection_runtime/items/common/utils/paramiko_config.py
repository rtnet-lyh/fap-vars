# -*- coding: utf-8 -*-

import io


def paramiko_auth_attempts(auth_method):
    method = str(auth_method or 'auto').strip().lower()
    if method == 'auto':
        return ['key', 'password']
    if method in ('key', 'password'):
        return [method]
    raise ValueError(f'unsupported paramiko auth_method: {auth_method}')


def load_paramiko_private_key(private_key, passphrase, paramiko_module):
    key_stream = io.StringIO(str(private_key))
    key_classes = [
        paramiko_module.RSAKey,
        paramiko_module.ECDSAKey,
        paramiko_module.Ed25519Key,
    ]
    dss_key = getattr(paramiko_module, 'DSSKey', None)
    if dss_key:
        key_classes.append(dss_key)

    last_error = None
    for key_cls in key_classes:
        key_stream.seek(0)
        try:
            return key_cls.from_private_key(key_stream, password=passphrase or None)
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError('unsupported private key')
