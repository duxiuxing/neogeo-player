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
    # 计算指定文件的 CRC32 值
    # Args:
    #     file_path (str): 文件路径，通常是 .zip 格式的 ROM 文件
    # Returns:
    #     str: 文件的 CRC32 值，八位大写十六进制字符串
    with open(file_path, 'rb') as file:
        data = file.read()
        crc = zlib.crc32(data)
        crc32 = hex(crc & 0xFFFFFFFF)[2:].upper()
        return crc32.rjust(8, "0")


class ConsoleBase(ConsoleConfigs):
    def __init__(self):
        # WiiFow 类型的实例，在子类的构造函数中创建。
        self.wiiflow = None

        # CRC32 值为键，GameInfo 为值的字典
        # 内容来自 roms\\all.xml
        # 读取操作在 self.reset_zip_crc32_to_game_info() 中实现
        self.zip_crc32_to_game_info = {}

    def reset_zip_crc32_to_game_info(self):
        # 本函数执行的操作如下：
        # 1. 清空 self.zip_crc32_to_game_info
        # 2. 读取 roms\\all.xml
        # 3. 重新填充 self.zip_crc32_to_game_info
        self.zip_crc32_to_game_info.clear()

        xml_file_path = os.path.join(
            self.root_folder_path(), "roms\\all.xml")
        if os.path.exists(xml_file_path):
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            for element in root.iter():
                if element.tag == "Game":
                    game_info = GameInfo(
                        zip_crc32=element.get("crc32").rjust(8, "0"),
                        zip_bytes=element.get("bytes"),
                        zip_title=element.get("zip"),
                        en_title=element.get("en"),
                        zhcn_title=element.get("zhcn"))
                    self.zip_crc32_to_game_info[game_info.zip_crc32] = game_info

    def verify_zip_file_name_as_crc32(self, zip_title):
        # 以《1941》这个游戏的 ROM 文件（.zip 格式）为例：
        # 情况1. 当游戏和 ROM 文件一一对应时，文件路径是：cps-player\\cps1\\roms\\1941.zip
        # 情况2. 当游戏对应的 ROM 文件不止一个时，需要先创建一个 1941 的文件夹，然后把
        #        不同的ROM 文件以 CRC32 值命名，放到这个文件夹里，例如：
        #          - roms\\1941\\64E58DC3.zip
        #          - roms\\1941\\8C733532.zip
        #          - roms\\1941\\9DA9C6D9.zip
        #
        # 本函数仅在 self.import_new_roms() 中调用，用来把情况1的 ROM 文件按照情况2的规则重命名
        zip_folder_path = os.path.join(
            self.root_folder_path(), f"roms\\{zip_title}")
        if not os.path.exists(zip_folder_path):
            os.makedirs(zip_folder_path)

        default_zip_path = os.path.join(
            self.root_folder_path(), f"roms\\{zip_title}.zip")
        if os.path.exists(default_zip_path):
            dst_zip_path = os.path.join(
                zip_folder_path, f"{compute_crc32(default_zip_path)}.zip")
            os.rename(default_zip_path, dst_zip_path)

    def import_new_roms(self):
        # 本函数用于导入 new_roms 文件夹里的游戏文件（.zip 格式）
        # 1. 新的游戏文件会被转移到 roms 文件夹，对应的 GameInfo 会
        #    记录在 new_roms.xml，需要进一步手动合入 roms\\all.xml；
        # 2. 已经有的游戏文件不会被转移，对应的 GameInfo 会记录在 exist_roms.xml
        self.reset_zip_crc32_to_game_info()

        exist_zip_crc32_to_name = {}
        new_roms_xml_root = ET.Element("Game-List")

        new_roms_folder_path = os.path.join(
            self.root_folder_path(), "new_roms")
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
                exist_zip_crc32_to_name[zip_crc32] = zip_file_name
                continue

            zip_title = os.path.splitext(zip_file_name)[0]

            en_title = ""
            zhcn_title = ""

            wii_game_info = self.wiiflow.find_game_info(zip_title, zip_crc32)
            if wii_game_info is not None:
                en_title = wii_game_info.en_title
                zhcn_title = wii_game_info.zhcn_title

            attribs = {
                "crc32": zip_crc32,
                "bytes": str(os.stat(zip_file_path).st_size),
                "zip": zip_title,
                "en": en_title,
                "zhcn": zhcn_title
            }
            ET.SubElement(new_roms_xml_root, "Game", attribs)

            dst_file_path = os.path.join(
                self.root_folder_path(), f"roms\\{zip_title}.zip")
            if os.path.exists(dst_file_path):
                self.verify_zip_file_name_as_crc32(zip_title)
                dst_file_path = os.path.join(
                    self.root_folder_path(), f"roms\\{zip_title}\\{zip_crc32}.zip")
            else:
                zip_title_folder_path = os.path.join(
                    self.root_folder_path(), f"roms\\{zip_title}")
                if os.path.exists(zip_title_folder_path):
                    dst_file_path = os.path.join(
                        zip_title_folder_path, f"{zip_crc32}.zip")
            os.rename(zip_file_path, dst_file_path)
            new_roms_count = new_roms_count + 1

        xml_file_path = os.path.join(new_roms_folder_path, "exist_roms.xml")
        if os.path.exists(xml_file_path):
            os.remove(xml_file_path)

        if len(exist_zip_crc32_to_name) > 0:
            exist_roms_xml_root = ET.Element("Game-List")
            for zip_crc32, zip_name in exist_zip_crc32_to_name.items():
                game_info = self.zip_crc32_to_game_info[zip_crc32]
                attribs = {
                    "crc32": game_info.zip_crc32,
                    "bytes": game_info.zip_bytes,
                    "zip": game_info.zip_title,
                    "en": game_info.en_title,
                    "zhcn": game_info.zhcn_title
                }
                ET.SubElement(exist_roms_xml_root, "Game", attribs)
                print(f"{zip_name} 已经存在，crc32 = {zip_crc32}")
            ET.ElementTree(exist_roms_xml_root).write(
                xml_file_path, encoding="utf-8", xml_declaration=True)

        xml_file_path = os.path.join(new_roms_folder_path, "new_roms.xml")
        if os.path.exists(xml_file_path):
            os.remove(xml_file_path)

        if new_roms_count == 0:
            print("没有新游戏")
            return
        else:
            print(f"发现 {new_roms_count} 个新游戏")
            ET.ElementTree(new_roms_xml_root).write(
                xml_file_path, encoding="utf-8", xml_declaration=True)

    def check_exist_games_infos(self):
        # WiiFlow 里有当前机种所有游戏的详细信息，本函数用于检查 roms\\all.xml 里
        # 的游戏中英文名称和 WiiFlow 里的是否一致，如果不一致则打印出来
        self.reset_zip_crc32_to_game_info()

        for zip_crc32, game_info in self.zip_crc32_to_game_info.items():
            wii_game_info = self.wiiflow.find_game_info(
                game_info.zip_title, zip_crc32)
            if wii_game_info is not None:
                if wii_game_info.en_title != game_info.en_title:
                    print("en 属性不一致")
                    print(f"\t{game_info.en_title} 在 all.xml")
                    print(
                        f"\t{wii_game_info.en_title} 在 {self.wiiflow.plugin_name}.xml")

                if wii_game_info.zhcn_title != game_info.zhcn_title:
                    print("zhcn 属性不一致")
                    print(f"\t{game_info.zhcn_title} 在 all.xml")
                    print(
                        f"\t{wii_game_info.zhcn_title} 在 {self.wiiflow.plugin_name}.xml")
