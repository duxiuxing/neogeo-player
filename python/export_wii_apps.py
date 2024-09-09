# -- coding: UTF-8 --

import os
import shutil

from console import Console
from helper import Helper
from local_configs import LocalConfigs
from main_menu import CmdHandler
from main_menu import MainMenu


class ExportWiiApps(CmdHandler):
    def __init__(self, files_tuple):
        super().__init__("Wii - 导出 - 模拟器 APP")
        self.files_tuple = files_tuple

    def run(self):
        wii_folder_path = os.path.join(
            MainMenu.console.root_folder_path(), "wii")
        for relative_path in self.files_tuple:
            src_path = os.path.join(wii_folder_path, relative_path)
            dst_path = os.path.join(LocalConfigs.sd_path(), relative_path)

            if os.path.isdir(src_path):
                Helper.copy_folder(src_path, dst_path)
            elif os.path.isfile(src_path):
                Helper.copy_file(src_path, dst_path)
