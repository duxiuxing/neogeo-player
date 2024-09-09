# -- coding: UTF-8 --

import fnmatch
import os
import shutil
import xml.etree.ElementTree as ET

from console import Console
from game_info import GameInfo
from helper import Helper
from local_configs import LocalConfigs
from wiiflow import WiiFlow


class ConsoleImpl(Console):
    def __init__(self):
        self._wiiflow = self.create_wiiflow()
        # 以下两个字典的内容都来自 roms 文件夹里的各个 .xml
        # 设置操作都在 self.reset_roms_crc32_to_path_and_game_info() 里
        self.roms_crc32_to_path = {}        # rom_crc32 为键，rom_path 为值的字典
        self.roms_crc32_to_game_info = {}   # rom_crc32 为键，GameInfo 为值的字典

    def create_wiiflow(self):
        raise NotImplementedError()

    def wiiflow(self):
        return self._wiiflow

    def load_roms_xml(self, xml_path):
        if not os.path.exists(xml_path):
            return

        tree = ET.parse(xml_path)
        root = tree.getroot()
        for game_elem in root.findall("Game"):
            rom_crc32 = game_elem.get("crc32").rjust(8, "0")
            rom_title = game_elem.get("rom")

            roms_folder_path = os.path.dirname(xml_path)
            rom_path = os.path.join(roms_folder_path,
                                    f"{rom_title}{self.rom_extension()}")
            if not os.path.exists(rom_path):
                rom_path = os.path.join(roms_folder_path,
                                        f"{rom_title}\\{rom_crc32}{self.rom_extension()}")
                if not os.path.exists(rom_path):
                    print(f"无效的文件 {rom_path}")

            self.roms_crc32_to_path[rom_crc32] = rom_path

            game_info = GameInfo(rom_crc32=rom_crc32,
                                 rom_bytes=game_elem.get("bytes"),
                                 rom_title=rom_title,
                                 en_title=game_elem.get("en"),
                                 zhcn_title=game_elem.get("zhcn"))
            self.roms_crc32_to_game_info[rom_crc32] = game_info

    def reset_roms_crc32_to_path_and_game_info(self):
        # 本函数执行的操作如下：
        # 1. 清空 self.roms_crc32_to_path 和 self.roms_crc32_to_game_info
        # 2. 读取 roms 文件夹里的各个 .xml
        # 3. 重新设置 self.roms_crc32_to_path 和 self.roms_crc32_to_game_info
        self.roms_crc32_to_path.clear()
        self.roms_crc32_to_game_info.clear()

        xml_path = os.path.join(self.root_folder_path(),
                                "roms\\roms.xml")
        self.load_roms_xml(xml_path)

        for letter in "#ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            xml_path = os.path.join(self.root_folder_path(),
                                    "roms\\{letter}\\{letter}.xml")
            self.load_roms_xml(xml_path)

    def query_rom_path(self, rom_crc32):
        if len(self.roms_crc32_to_path) == 0:
            self.reset_roms_crc32_to_path_and_game_info()

        if rom_crc32 in self.roms_crc32_to_path.keys():
            return self.roms_crc32_to_path[rom_crc32]
        else:
            return None

    def verify_rom_name_as_crc32(self, old_rom_path):
        # 以《1941》这个游戏的 ROM 文件（1941.zip）为例：
        # 情况1. 当游戏和 ROM 文件一一对应时，ROM 文件路径是：cps-player\\cps1\\roms\\1941.zip
        # 情况2. 当游戏对应的 ROM 文件不止一个时，需要先创建一个 1941 的文件夹，然后把
        #        不同的 ROM 文件以 CRC32 值命名，放到这个文件夹里，例如：
        #          - roms\\1941\\64E58DC3.zip
        #          - roms\\1941\\8C733532.zip
        #          - roms\\1941\\9DA9C6D9.zip
        #
        # 本函数仅在 self.import_roms() 中调用，用来把情况1的 ROM 文件按照情况2的规则重命名
        rom_crc32 = Helper.compute_crc32(old_rom_path)
        rom_name = os.path.basename(old_rom_path)
        rom_title = os.path.splitext(rom_name)[0]
        rom_extension = os.path.splitext(rom_name)[1]

        new_rom_path = os.path.join(os.path.dirname(old_rom_path),
                                    f"{rom_title}\\{rom_crc32}{rom_extension}")
        if Helper.verify_folder_exist_ex(os.path.dirname(new_rom_path)):
            os.rename(old_rom_path, new_rom_path)
            self.roms_crc32_to_path[rom_crc32] = new_rom_path

    def rom_parent_folder_path(self, rom_title):
        xml_path = os.path.join(self.root_folder_path(),
                                "roms\\roms.xml")
        if os.path.exists(xml_path):
            return os.path.join(self.root_folder_path(),
                                "roms")
        else:
            letter = rom_title.upper()[0]
            if letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                letter = "#"
            return os.path.join(self.root_folder_path(),
                                "roms\\{letter}")

    def import_roms(self):
        # 本函数用于导入 roms_import 文件夹里的 ROM 文件
        # 1. 新的 ROM 文件会被转移到 roms 文件夹，对应的 GameInfo 会
        #    记录在 roms_new.xml，需要进一步手动合入 roms.xml；
        # 2. 已经有的游戏文件不会被转移，对应的 GameInfo 会记录在 roms_exist.xml
        self.reset_roms_crc32_to_path_and_game_info()

        exist_roms_crc32_to_name = {}
        new_roms_xml_root = ET.Element("Game-List")

        import_folder_path = os.path.join(
            self.root_folder_path(), "roms_import")
        if not os.path.exists(import_folder_path):
            print(f"无效的文件夹：{import_folder_path}")
            return

        new_roms_count = 0
        for src_rom_name in os.listdir(import_folder_path):
            if not self.rom_extension_match(src_rom_name):
                continue

            src_rom_path = os.path.join(import_folder_path, src_rom_name)
            src_rom_crc32 = Helper.compute_crc32(src_rom_path)
            if src_rom_crc32 in self.roms_crc32_to_game_info.keys():
                exist_roms_crc32_to_name[src_rom_crc32] = src_rom_name
                continue

            src_rom_bytes = str(os.stat(src_rom_path).st_size)
            src_rom_title = os.path.splitext(src_rom_name)[0]
            src_rom_extension = os.path.splitext(src_rom_name)[1]

            game_info = self.wiiflow().plugins_data().query_game_info(rom_crc32=src_rom_crc32,
                                                                      rom_title=src_rom_title,
                                                                      en_title=src_rom_title,
                                                                      zhcn_title=src_rom_title)
            if game_info is None:
                print(f"未知的游戏 crc32=\"{src_rom_crc32}\" bytes=\"{src_rom_bytes}\"\n\trom=\"{src_rom_title}\"")
                continue

            en_title = game_info.en_title
            zhcn_title = game_info.zhcn_title

            attribs = {
                "crc32": src_rom_crc32,
                "bytes": src_rom_bytes,
                "rom": game_info.rom_title,
                "en": en_title,
                "zhcn": zhcn_title
            }
            if len(src_rom_title) > 3 and src_rom_title[-3:] == "(中)":
                attribs["language"] = "chinese"
            ET.SubElement(new_roms_xml_root, "Game", attribs)
            self.roms_crc32_to_game_info[src_rom_crc32] = GameInfo(rom_crc32=src_rom_crc32,
                                                                   rom_bytes=src_rom_bytes,
                                                                   rom_title=game_info.rom_title,
                                                                   en_title=en_title,
                                                                   zhcn_title=zhcn_title)

            if src_rom_title == game_info.rom_title:
                print(f"新游戏入库 {src_rom_name}，crc32 = {src_rom_crc32}")
            else:
                print(f"新游戏 {src_rom_name} 官方名称为 {game_info.rom_title}，crc32 = {src_rom_crc32}")

            rom_parent_folder_path = self.rom_parent_folder_path(game_info.rom_title)
            dst_rom_path = os.path.join(rom_parent_folder_path,
                                        f"{game_info.rom_title}{src_rom_extension}")
            if os.path.exists(dst_rom_path):
                # 如果已有的 ROM 文件是按照情况1的规则命名的，需要将已有的 ROM 文件按照情况2的规则重命名
                self.verify_rom_name_as_crc32(dst_rom_path)
                dst_rom_path = os.path.join(rom_parent_folder_path,
                                            f"{game_info.rom_title}\\{src_rom_crc32}{src_rom_extension}")
            else:
                # 如果已有的 ROM 文件是按照情况2的规则命名的，那新的 ROM 文件也按照情况2的规则重命名
                rom_folder_path = os.path.join(rom_parent_folder_path,
                                               f"{game_info.rom_title}")
                if os.path.exists(rom_folder_path):
                    dst_rom_path = os.path.join(rom_parent_folder_path,
                                                f"{game_info.rom_title}\\{src_rom_crc32}{src_rom_extension}")

            if os.path.exists(dst_rom_path):
                print(f"{src_rom_name}，crc32 = {src_rom_crc32} 已经存在，但不在 .xml 中")
            elif Helper.verify_folder_exist_ex(os.path.dirname(dst_rom_path)):
                os.rename(src_rom_path, dst_rom_path)
            new_roms_count = new_roms_count + 1

        xml_file_path = os.path.join(self.root_folder_path(), "roms_exist.xml")
        if os.path.exists(xml_file_path):
            os.remove(xml_file_path)

        if len(exist_roms_crc32_to_name) > 0:
            exist_roms_xml_root = ET.Element("Game-List")
            for rom_crc32, rom_name in exist_roms_crc32_to_name.items():
                game_info = self.roms_crc32_to_game_info[rom_crc32]
                attribs = {
                    "crc32": game_info.rom_crc32,
                    "bytes": game_info.rom_bytes,
                    "rom": game_info.rom_title,
                    "en": game_info.en_title,
                    "zhcn": game_info.zhcn_title
                }
                ET.SubElement(exist_roms_xml_root, "Game", attribs)
                print(f"{rom_name} 已经存在，官方名称为 {game_info.rom_title} crc32 = {rom_crc32}")
            ET.ElementTree(exist_roms_xml_root).write(xml_file_path, encoding="utf-8", xml_declaration=True)

        xml_file_path = os.path.join(self.root_folder_path(), "roms_new.xml")
        if os.path.exists(xml_file_path):
            os.remove(xml_file_path)

        if new_roms_count == 0:
            print("没有新游戏")
            return
        else:
            print(f"发现 {new_roms_count} 个新游戏")
            ET.ElementTree(new_roms_xml_root).write(xml_file_path, encoding="utf-8", xml_declaration=True)

    def check_exist_roms_infos(self):
        # WiiFlow 里有当前机种所有游戏的详细信息，本函数用于检查 roms.xml 中
        # 的游戏中英文名称和 WiiFlow 里的是否一致，如果不一致则打印出来
        self.reset_roms_crc32_to_path_and_game_info()

        for rom_crc32, rom_path in self.roms_crc32_to_path.items():
            rom_crc32_compute = Helper.compute_crc32(rom_path)
            if rom_crc32 != rom_crc32_compute:
                print(f"crc32 属性不一致，{rom_path}")
                print(f"\t{rom_crc32} 在 roms 文件夹里的 .xml 文件中")
                print(f"\t{rom_crc32_compute} 是实际计算出来的 crc32")

        for game_info in self.roms_crc32_to_game_info.values():
            # 检查 en 和 zhcn 属性是否一致
            db_game_info = self.wiiflow().plugins_data().query_game_info(rom_crc32=game_info.rom_crc32)
            if db_game_info is None:
                print(f"{self.wiiflow().plugin_name()}.ini 中缺失配置")
                print(f"{game_info.rom_title} = {game_info.rom_crc32}")
            else:
                if game_info.en_title != db_game_info.en_title:
                    print(f"en 属性不一致，rom_crc = {game_info.rom_crc32}")
                    print(f"\t{game_info.en_title} 在 roms 文件夹里的 .xml 文件中")
                    print(f"\t{db_game_info.en_title} 在 {self.wiiflow().plugin_name()}.xml")

                if game_info.zhcn_title != db_game_info.zhcn_title:
                    print(f"zhcn 属性不一致，rom_crc = {game_info.rom_crc32}")
                    print(f"\t{game_info.zhcn_title} 在 roms 文件夹里的 .xml 文件中")
                    print(f"\t{db_game_info.zhcn_title} 在 {self.wiiflow().plugin_name()}.xml")
