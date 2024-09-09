# -- coding: UTF-8 --

import os
import shutil
import xml.etree.ElementTree as ET

from console import Console
from helper import Helper
from local_configs import LocalConfigs
from main_menu import CmdHandler
from main_menu import MainMenu


class ExportNgpEmuCnRoms(CmdHandler):
    def __init__(self):
        super().__init__("NGP.emu.cn - 导出 - 中文命名的 ROM")

    def export_roms_by_xml(self, folder_elem, folder_path):
        # 本函数用于把 folder_elem 中所有的 ROM 文件导出到 dst_folder_path
        for game_elem in folder_elem.findall("Game"):
            rom_crc32 = game_elem.get("crc32").rjust(8, "0")
            src_rom_path = MainMenu.console.query_rom_path(rom_crc32)
            if src_rom_path is None:
                print(f"crc32 = {rom_crc32} 的 ROM 文件不存在")
                continue
            rom_name = game_elem.get("rom") + MainMenu.console.rom_extension()
            dst_rom_path = os.path.join(folder_path, rom_name)
            Helper.copy_file_if_not_exist(src_rom_path, dst_rom_path)

        for child_folder_elem in folder_elem.findall("Folder"):
            child_folder_path = os.path.join(
                folder_path, child_folder_elem.get("name"))
            Helper.verify_folder_exist(child_folder_path)
            self.export_roms_by_xml(child_folder_elem, child_folder_path)

    def run(self):
        # 本函数用于把 roms_export.xml 中所有的 ROM 文件导出到 SD 卡
        xml_path = os.path.join(MainMenu.console.root_folder_path(),
                                "NGP.emu.cn\\roms_export.xml")
        if not os.path.exists(xml_path):
            print(f"无效的文件：{xml_path}")
            return
        tree = ET.parse(xml_path)

        root_folder_path = os.path.join(LocalConfigs.sd_path(), "roms\\NGP")
        if not Helper.verify_folder_exist_ex(root_folder_path):
            return

        self.export_roms_by_xml(tree.getroot(), root_folder_path)
