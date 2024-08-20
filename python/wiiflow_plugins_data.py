# -- coding: UTF-8 --

import os
import xml.etree.ElementTree as ET

from game_info import GameInfo
from configparser import ConfigParser
from console import Console
from local_configs import LocalConfigs


def folder_exist(folder_path):
    # 判断指定文件夹是否存在
    # Args:
    #     folder_path (str): 待判断的文件夹路径
    # Returns:
    #     bool: 如果文件夹存在则返回 True，否则返回 False
    if os.path.isdir(folder_path):
        return True
    else:
        print(f"无效的文件夹：{folder_path}")
        return False


def verify_folder_exist(folder_path):
    # 判断指定文件夹是否存在，如果不存在则创建该文件夹
    # Args:
    #     folder_path (str): 待判断的文件夹路径，要求父文件夹必须是存在的
    # Returns:
    #     bool: 如果文件夹存在或创建成功，则返回 True，否则返回 False
    if os.path.isdir(folder_path):
        return True
    else:
        os.mkdir(folder_path)
        if os.path.isdir(folder_path):
            return True
        else:
            print(f"无效文件夹：{folder_path}")
            return False


class WiiFlowPluginsData:
    def __init__(self, console, plugin_name):
        self.console = console

        # 机种对应的 WiiFlow 插件名称
        self.plugin_name = plugin_name

        # 游戏 ID 为键，GameInfo 为值的字典
        # 内容来自 <self.plugin_name>.xml
        # 读取操作在 self.init_game_id_to_info() 中实现
        self.game_id_to_info = {}

        # CRC32 值和 .zip 文件标题为键，游戏 ID 为值的字典
        # 内容来自 <self.plugin_name>.ini
        # 读取操作在 self.init_rom_crc32_to_game_id() 中实现
        self.rom_crc32_to_game_id = {}

    def init_game_id_to_info(self):
        # 本函数执行的操作如下：
        # 1. 读取 <self.plugin_name>.xml
        # 2. 填写 self.game_id_to_info
        # 3. 有防止重复读取的逻辑
        if len(self.game_id_to_info) > 0:
            return

        xml_file_path = os.path.join(
            self.console.root_folder_path(),
            f"wiiflow\\plugins_data\\{self.plugin_name}\\{self.plugin_name}.xml")

        if not os.path.exists(xml_file_path):
            print(f"无效的文件：{xml_file_path}")
            return

        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        for game_elem in root.findall("game"):
            game_name = game_elem.get("name")
            game_id = ""
            en_title = ""
            zhcn_title = ""
            for elem in game_elem:
                if elem.tag == "id":
                    game_id = elem.text
                elif elem.tag == "locale":
                    lang = elem.get("lang")
                    if lang == "EN":
                        en_title = elem.find("title").text
                        if en_title not in game_name.split(" / "):
                            print("英文名不一致")
                            print(f"\tname     = {game_name}")
                            print(f"\tEN title = {en_title}")
                    elif lang == "ZHCN":
                        zhcn_title = elem.find("title").text

            self.game_id_to_info[game_id] = GameInfo(
                en_title=en_title, zhcn_title=zhcn_title)

    def init_rom_crc32_to_game_id(self):
        # 本函数执行的操作如下：
        # 1. 读取 <self.plugin_name>.ini
        # 2. 填写 self.rom_crc32_to_game_id
        # 3. 有防止重复读取的逻辑
        if len(self.rom_crc32_to_game_id) > 0:
            return

        ini_file_path = os.path.join(
            self.console.root_folder_path(),
            f"wiiflow\\plugins_data\\{self.plugin_name}\\{self.plugin_name}.ini")

        if not os.path.exists(ini_file_path):
            print(f"无效的文件：{ini_file_path}")
            return

        ini_parser = ConfigParser()
        ini_parser.read(ini_file_path)
        if ini_parser.has_section(self.plugin_name):
            for rom_title in ini_parser[self.plugin_name]:
                values = ini_parser[self.plugin_name][rom_title].split("|")
                game_id = values[0]
                self.rom_crc32_to_game_id[rom_title] = game_id
                if game_id in self.game_id_to_info.keys():
                    self.game_id_to_info[game_id].rom_name = f"{rom_title}{self.console.rom_extension()}"
                for index in range(1, len(values)):
                    rom_crc32 = values[index].rjust(8, "0")
                    self.rom_crc32_to_game_id[rom_crc32] = game_id

    def find_game_titles(self, rom_title, rom_crc32):
        # 根据 CRC32 值或 ROM 文件标题查找游戏的英文名和中文名
        # Args:
        #     rom_title (str): ROM 文件的标题，比如 1941.zip 的标题就是 1941，查找优先级低
        #     rom_crc32 (str): ROM 文件的 CRC32 值，查找优先级高
        # Returns:
        #     找到则返回 GameInfo 对象，仅以下字段有效：
        #         - GameInfo.rom_name   : ROM 文件名，如 1941.zip
        #         - GameInfo.en_title   : 游戏的英文名
        #         - GameInfo.zhcn_title : 游戏的中文名
        #
        #     没找到则返回 None
        self.init_game_id_to_info()         # 必须先于 init_rom_crc32_to_game_id() 调用
        # 内部会填写 self.game_id_to_info 每个 GameInfo 的 rom_name
        self.init_rom_crc32_to_game_id()

        game_id = None
        if rom_title in self.rom_crc32_to_game_id.keys():
            game_id = self.rom_crc32_to_game_id[rom_title]
        elif rom_crc32 in self.rom_crc32_to_game_id.keys():
            game_id = self.rom_crc32_to_game_id[rom_crc32]

        if game_id is not None and game_id in self.game_id_to_info.keys():
            return self.game_id_to_info[game_id]

        print(f"{rom_title} 不在 {self.plugin_name}.ini 中，crc32 = {rom_crc32}")
        return None

    def export_all_fake_roms(self):
        # 本函数会根据 <plugin_name>.ini 创建空白的 .zip 文件并导出到 Wii 的 SD 卡
        # 主要是为了方便在 WiiFlow 中展示所有游戏封面，而不需要在 SD 卡里装上所有游戏
        ini_file_path = os.path.join(
            self.console.root_folder_path(),
            f"wiiflow\\plugins_data\\{self.plugin_name}\\{self.plugin_name}.ini")

        if not os.path.exists(ini_file_path):
            print(f"无效的文件：{ini_file_path}")
            return

        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\roms
        dst_roms_folder_path = os.path.join(
            LocalConfigs.sd_path(), "roms")
        if not verify_folder_exist(dst_roms_folder_path):
            return

        # SD:\\roms\\<plugin_name>
        roms_plugin_name_folder_path = os.path.join(
            dst_roms_folder_path, self.plugin_name)
        if not verify_folder_exist(roms_plugin_name_folder_path):
            return

        ini_parser = ConfigParser()
        ini_parser.read(ini_file_path)
        if ini_parser.has_section(self.plugin_name) is False:
            print(f"[{self.plugin_name}] 不存在于 {ini_file_path}")
            return
        for rom_title in ini_parser[self.plugin_name]:
            dst_zip_path = os.path.join(
                roms_plugin_name_folder_path,
                f"{rom_title}{self.console.rom_extension()}")
            if not os.path.exists(dst_zip_path):
                open(dst_zip_path, "w").close()
