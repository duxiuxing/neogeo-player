# -- coding: UTF-8 --


class GameInfo:
    def __init__(self, zip_crc32="", zip_bytes="", zip_title="", en_title="", zhcn_title=""):
        self.zip_crc32 = zip_crc32
        self.zip_bytes = zip_bytes
        self.zip_title = zip_title
        self.en_title = en_title
        self.zhcn_title = zhcn_title
