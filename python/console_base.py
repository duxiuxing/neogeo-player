# -- coding: UTF-8 --

import fnmatch
import os
import shutil
import xml.etree.ElementTree as ET
import zlib

from console_configs import ConsoleConfigs
from game_info import GameInfo
from local_configs import LocalConfigs
from wiiflow import WiiFlow


def compute_crc32(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
        crc = zlib.crc32(data)
        crc32 = hex(crc & 0xFFFFFFFF)[2:].upper()
        return crc32.rjust(8, "0")


def create_folder_if_not_exists(folder_full_path):
    folder_path = ""
    for folder_name in folder_full_path.split("\\"):
        if folder_path == "":
            folder_path = folder_name
            if not os.path.exists(folder_path):
                return False
        else:
            if not os.path.exists(folder_path):
                return False
            folder_path = f"{folder_path}\\{folder_name}"
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)
    return os.path.exists(folder_full_path)


def copy_folder(src, dst):
    if not create_folder_if_not_exists(dst):
        return
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copy_folder(s, d)
        elif not os.path.exists(d):
            shutil.copy2(s, d)


def copy_file(src, dst):
    if not create_folder_if_not_exists(os.path.dirname(dst)):
        return
    if not os.path.exists(dst):
        shutil.copy2(src, dst)


class ConsoleBase(ConsoleConfigs):
    def __init__(self):
        self.zip_crc32_to_game_info = {}

    def reset_zip_crc32_to_game_info(self):
        self.zip_crc32_to_game_info.clear()

        xml_file_path = os.path.join(
            self.folder_path(), "roms\\all.xml")
        if os.path.exists(xml_file_path):
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            for element in root.iter():
                if element.tag == "Game":
                    zip_crc32 = element.get("crc32").rjust(8, "0")
                    zip_title = element.get("zip")
                    en_title = element.get("en")
                    zhcn_title = element.get("zhcn")
                    game_info = GameInfo(en_title, zhcn_title)
                    game_info.zip_title = zip_title
                    self.zip_crc32_to_game_info[zip_crc32] = game_info

    def verify_default_zip_name_as_crc32(self, zip_title):
        zip_folder_path = os.path.join(
            self.folder_path(), f"roms\\{zip_title}")
        if not os.path.exists(zip_folder_path):
            os.makedirs(zip_folder_path)

        default_zip_path = os.path.join(
            self.folder_path(), f"roms\\{zip_title}.zip")
        if os.path.exists(default_zip_path):
            dst_zip_path = os.path.join(
                zip_folder_path, f"{compute_crc32(default_zip_path)}.zip")
            os.rename(default_zip_path, dst_zip_path)

    def import_new_roms(self):
        self.reset_zip_crc32_to_game_info()
        wiiflow = WiiFlow(self)

        exist_roms_crc32_to_zip = {}
        xml_root = ET.Element("Game-List")

        new_roms_folder_path = os.path.join(self.folder_path(), "new_roms")
        if not os.path.exists(new_roms_folder_path):
            print(f"无效的文件夹：{new_roms_folder_path}")
            return

        new_roms_count = 0
        for zip_file_name in os.listdir(new_roms_folder_path):
            if not fnmatch.fnmatch(zip_file_name, "*.zip"):
                continue

            zip_file_path = os.path.join(new_roms_folder_path, zip_file_name)
            zip_crc32 = compute_crc32(zip_file_path)
            if zip_crc32 in self.zip_crc32_to_game_info.keys():
                exist_roms_crc32_to_zip[zip_crc32] = zip_file_name
                continue

            zip_title = os.path.splitext(zip_file_name)[0]

            en_title = ""
            zhcn_title = ""

            wii_game_info = wiiflow.find_game_info(zip_title, zip_crc32)
            if wii_game_info is not None:
                en_title = wii_game_info.en_title
                zhcn_title = wii_game_info.zhcn_title

            attrib = {
                "crc32": zip_crc32,
                "bytes": str(os.stat(zip_file_path).st_size),
                "zip": zip_title,
                "en": en_title,
                "zhcn": zhcn_title
            }

            xml_elem = ET.SubElement(xml_root, "Game", attrib)

            dst_file_path = os.path.join(
                self.folder_path(), f"roms\\{zip_title}.zip")
            if os.path.exists(dst_file_path):
                self.verify_default_zip_name_as_crc32(zip_title)
                dst_file_path = os.path.join(
                    self.folder_path(), f"roms\\{zip_title}\\{zip_crc32}.zip")
            os.rename(zip_file_path, dst_file_path)
            new_roms_count = new_roms_count + 1

        for key, value in exist_roms_crc32_to_zip.items():
            print(f"{value} 已经存在，crc32 = {key}")

        xml_file_path = os.path.join(new_roms_folder_path, "new_roms.xml")
        if os.path.exists(xml_file_path):
            os.remove(xml_file_path)

        if new_roms_count == 0:
            print("没有新游戏")
            return
        else:
            print(f"发现 {new_roms_count} 个新游戏")
            tree = ET.ElementTree(xml_root)
            tree.write(xml_file_path, encoding="utf-8", xml_declaration=True)

    def check_game_infos(self):
        self.reset_zip_crc32_to_game_info()
        wiiflow = WiiFlow(self)

        for zip_crc32, game_info in self.zip_crc32_to_game_info.items():
            wii_game_info = wiiflow.find_game_info(
                game_info.zip_title, zip_crc32)
            if wii_game_info is not None:
                if wii_game_info.en_title != game_info.en_title:
                    print("en 属性不匹配")
                    print(f"\t{game_info.en_title} 在 all.xml")
                    print(
                        f"\t{wii_game_info.en_title} 在 {self.wiiflow_plugin_name()}.xml")

                if wii_game_info.zhcn_title != game_info.zhcn_title:
                    print("zhcn 属性不匹配")
                    print(f"\t{game_info.zhcn_title} 在 all.xml")
                    print(
                        f"\t{wii_game_info.zhcn_title} 在 {self.wiiflow_plugin_name()}.xml")

    def export_wii_app(self, files_tuple):
        wii_folder_path = os.path.join(self.folder_path(), "wii")
        for relative_path in files_tuple:
            src_path = os.path.join(wii_folder_path, relative_path)
            dst_path = os.path.join(LocalConfigs.SDCARD_ROOT, relative_path)

            if not os.path.exists(src_path):
                print(f"源文件缺失：{src_path}")
                continue

            if os.path.isdir(src_path):
                copy_folder(src_path, dst_path)
            elif os.path.isfile(src_path):
                copy_file(src_path, dst_path)

    def main_menu(self, wii_app_files_tuple):
        while True:
            print(f"\n\n机种代码：{self.wiiflow_plugin_name()}\n请输入数字序号，选择要执行的操作：")
            print("\t1. 导出空白的.zip文件 WiiFlow.export_fake_roms()")
            print("\t2. 导入新游戏 Console.import_new_roms()")
            print("\t3. 检查游戏信息 Console.check_game_infos()")
            print("\t4. 转换封面图片 WiiFlow.convert_wfc_files()")
            print("\t5. 导出 WiiFlow 的演示文件 WiiFlow.export_all(with_fake_roms = True)")
            print("\t6. 导出 WiiFlow 的发布文件 WiiFlow.export_all(with_real_roms = False)")
            print("\t7. 导出 Wii APP 的文件 Console.export_wii_app()")
            print("\t8. 退出程序")

            input_value = str(input("Enter the version number: "))
            if input_value == "1":
                wiiflow = WiiFlow(self)
                wiiflow.export_fake_roms()
            elif input_value == "2":
                self.import_new_roms()
            elif input_value == "3":
                self.check_game_infos()
            elif input_value == "4":
                wiiflow = WiiFlow(self)
                wiiflow.convert_wfc_files()
            elif input_value == "5":
                wiiflow = WiiFlow(self)
                wiiflow.export_all(True)
            elif input_value == "6":
                wiiflow = WiiFlow(self)
                wiiflow.export_all(False)
            elif input_value == "7":
                self.export_wii_app(wii_app_files_tuple)
            elif input_value == "8":
                break
