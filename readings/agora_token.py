"""
Pure-Python Agora RTC/RTM token builder.
Implements Agora's token generation algorithm without external dependencies.
"""
import hmac
import hashlib
import struct
import random
import time
import zlib
import base64
from io import BytesIO


VERSION_LENGTH = 3
APP_ID_LENGTH = 32

ROLE_PUBLISHER = 1
ROLE_SUBSCRIBER = 2

PRIVILEGE_JOIN_CHANNEL = 1
PRIVILEGE_PUBLISH_AUDIO_STREAM = 2
PRIVILEGE_PUBLISH_VIDEO_STREAM = 3
PRIVILEGE_PUBLISH_DATA_STREAM = 4
PRIVILEGE_LOGIN_RTM = 1000


def _pack_uint16(value):
    return struct.pack('<H', value)


def _pack_uint32(value):
    return struct.pack('<I', value)


def _pack_string(s):
    if isinstance(s, str):
        s = s.encode('utf-8')
    return _pack_uint16(len(s)) + s


def _pack_map_uint32(m):
    result = _pack_uint16(len(m))
    for key, value in sorted(m.items()):
        result += _pack_uint16(key)
        result += _pack_uint32(value)
    return result


class AccessToken:
    def __init__(self, app_id, app_certificate, channel_name, uid):
        self.app_id = app_id
        self.app_certificate = app_certificate
        self.channel_name = channel_name
        if uid == 0:
            self.account = ""
        else:
            self.account = str(uid)
        self.salt = random.randint(1, 0xFFFFFFFF)
        self.ts = int(time.time()) + 24 * 3600
        self.privileges = {}

    def add_privilege(self, privilege, expire_timestamp):
        self.privileges[privilege] = expire_timestamp

    def build(self):
        m = (
            self.app_id.encode('utf-8')
            + _pack_uint32(self.ts)
            + _pack_uint32(self.salt)
            + _pack_string(self.channel_name)
            + _pack_string(self.account)
            + _pack_map_uint32(self.privileges)
        )
        signing = hmac.new(self.app_certificate.encode('utf-8'), m, hashlib.sha256).digest()

        content = (
            _pack_string(self.app_id)
            + _pack_uint32(self.ts)
            + _pack_uint32(self.salt)
            + _pack_string(self.channel_name)
            + _pack_string(self.account)
            + _pack_map_uint32(self.privileges)
        )

        compressed = zlib.compress(signing + content)
        token = "006" + self.app_id + base64.b64encode(compressed).decode('utf-8')
        return token


class RtcTokenBuilder:
    @staticmethod
    def build_token_with_uid(app_id, app_certificate, channel_name, uid, role, privilege_expire_ts):
        token = AccessToken(app_id, app_certificate, channel_name, uid)
        token.add_privilege(PRIVILEGE_JOIN_CHANNEL, privilege_expire_ts)
        if role == ROLE_PUBLISHER:
            token.add_privilege(PRIVILEGE_PUBLISH_AUDIO_STREAM, privilege_expire_ts)
            token.add_privilege(PRIVILEGE_PUBLISH_VIDEO_STREAM, privilege_expire_ts)
            token.add_privilege(PRIVILEGE_PUBLISH_DATA_STREAM, privilege_expire_ts)
        return token.build()

    @staticmethod
    def build_token_with_account(app_id, app_certificate, channel_name, account, role, privilege_expire_ts):
        token = AccessToken(app_id, app_certificate, channel_name, 0)
        token.account = account
        token.add_privilege(PRIVILEGE_JOIN_CHANNEL, privilege_expire_ts)
        if role == ROLE_PUBLISHER:
            token.add_privilege(PRIVILEGE_PUBLISH_AUDIO_STREAM, privilege_expire_ts)
            token.add_privilege(PRIVILEGE_PUBLISH_VIDEO_STREAM, privilege_expire_ts)
            token.add_privilege(PRIVILEGE_PUBLISH_DATA_STREAM, privilege_expire_ts)
        return token.build()


class RtmTokenBuilder:
    @staticmethod
    def build_token(app_id, app_certificate, account, expire_ts):
        token = AccessToken(app_id, app_certificate, "", 0)
        token.account = account
        token.add_privilege(PRIVILEGE_LOGIN_RTM, expire_ts)
        return token.build()
