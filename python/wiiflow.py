# -- coding: UTF-8 --

import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

from game_info import GameInfo
from configparser import ConfigParser
from console_configs import ConsoleConfigs
from local_configs import LocalConfigs


def verify_folder_exist(folder_path):
    if os.path.isdir(folder_path):
        return True
    else:
        print(f"无效的文件夹：{folder_path}")
        return False


def create_folder_if_not_exist(folder_path):
    if os.path.isdir(folder_path):
        return True
    else:
        os.mkdir(folder_path)
        return os.path.isdir(folder_path)


class WiiFlow:
    def __init__(self, console_configs):
        self.console_configs = console_configs
        self.zip_crc32_to_game_id = {}
        self.game_id_to_info = {}
        self.zip_title_to_path = {}

    # 根据 <plugin_name>.ini 的内容构造 zip_title / zip_crc32 到 game_id 的字典
    def init_zip_crc32_to_game_id(self):
        if len(self.zip_crc32_to_game_id) > 0:
            return

        plugin_name = self.console_configs.wiiflow_plugin_name()
        ini_file_path = os.path.join(
            self.console_configs.folder_path(),
            f"wiiflow\\plugins_data\\{plugin_name}\\{plugin_name}.ini")

        if not os.path.exists(ini_file_path):
            print(f"无效的文件：{ini_file_path}")
            return

        ini_parser = ConfigParser()
        ini_parser.read(ini_file_path)
        if ini_parser.has_section(plugin_name):
            for zip_title in ini_parser[plugin_name]:
                values = ini_parser[plugin_name][zip_title].split("|")
                game_id = values[0]
                self.zip_crc32_to_game_id[zip_title] = game_id
                for index in range(1, len(values)):
                    self.zip_crc32_to_game_id[values[index].rjust(
                        8, "0")] = game_id

    # 根据 <plugin_name>.xml 的内容构造 game_id 到 GameInfo 的字典
    def init_game_id_to_info(self):
        if len(self.game_id_to_info) > 0:
            return

        xml_file_path = os.path.join(
            self.console_configs.folder_path(),
            f"wiiflow\\plugins_data\\{self.console_configs.wiiflow_plugin_name()}\\{self.console_configs.wiiflow_plugin_name()}.xml")

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
                        if game_name != en_title:
                            print("英文名不一致")
                            print(f"\tname     = {game_name}")
                            print(f"\tEN title = {en_title}")
                    elif lang == "ZHCN":
                        zhcn_title = elem.find("title").text

            self.game_id_to_info[game_id] = GameInfo(en_title, zhcn_title)

    def init_zip_title_to_path(self):
        if len(self.zip_title_to_path) > 0:
            return

        xml_file_path = os.path.join(
            self.console_configs.folder_path(), "wiiflow\\wiiflow.xml")

        if not os.path.exists(xml_file_path):
            print(f"无效的文件：{xml_file_path}")
            return

        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        for game_elem in root.findall("Game"):
            zip_crc32 = game_elem.get("crc32").rjust(8, "0")
            zip_title = game_elem.get("zip")
            if zip_title is None:
                print(f"crc32 = {zip_crc32} 的元素缺少 zip 属性")
                continue
            zip_path = os.path.join(
                self.console_configs.folder_path(), f"roms\\{zip_title}.zip")
            if not os.path.exists(zip_path):
                zip_path = os.path.join(
                    self.console_configs.folder_path(), f"roms\\{zip_title}\\{zip_crc32}.zip")
                if not os.path.exists(zip_path):
                    print(f"无效的文件：{zip_path}")
                    continue

            self.zip_title_to_path[zip_title] = zip_path

    def convert_wfc_files(self):
        if not os.path.exists(LocalConfigs.WFC_CONV_EXE):
            print(f"无效的文件：{LocalConfigs.WFC_CONV_EXE}")
            zip_file_path = os.path.join(
                LocalConfigs.REPOSITORY_FOLDER, "pc-tool\\WFC_conv_0-1.zip")
            print(f"安装文件在 {zip_file_path}")
            return

        # wiiflow
        wiiflow_foler_path = os.path.join(
            self.console_configs.folder_path(), "wiiflow")
        if not create_folder_if_not_exist(wiiflow_foler_path):
            print(f"无效文件夹：{wiiflow_foler_path}")
            return

        # wiiflow\\cache
        cache_folder_path = os.path.join(wiiflow_foler_path, "cache")
        if not create_folder_if_not_exist(cache_folder_path):
            print(f"无效文件夹：{cache_folder_path}")
            return

        cmd_line = f"\"{LocalConfigs.WFC_CONV_EXE}\" \"{wiiflow_foler_path}\""
        print(cmd_line)
        subprocess.call(cmd_line)

    def export_roms(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\roms
        dst_roms_folder_path = os.path.join(LocalConfigs.SDCARD_ROOT, "roms")
        if not create_folder_if_not_exist(dst_roms_folder_path):
            return

        # SD:\\roms\\<plugin_name>
        dst_folder_path = os.path.join(
            dst_roms_folder_path, self.console_configs.wiiflow_plugin_name())
        if not create_folder_if_not_exist(dst_folder_path):
            return
        for zip_title, src_zip_path in self.zip_title_to_path.items():
            dst_zip_path = os.path.join(dst_folder_path, f"{zip_title}.zip")
            if not os.path.exists(dst_zip_path):
                shutil.copyfile(src_zip_path, dst_zip_path)

    # 根据 <plugin_name>.ini 的内容构造创建空白的 .zip 文件
    def export_fake_roms(self):
        plugin_name = self.console_configs.wiiflow_plugin_name()
        ini_file_path = os.path.join(
            self.console_configs.folder_path(),
            f"wiiflow\\plugins_data\\{plugin_name}\\{plugin_name}.ini")

        if not os.path.exists(ini_file_path):
            print(f"无效的文件：{ini_file_path}")
            return

        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\fake_roms
        dst_roms_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "fake_roms")
        if not create_folder_if_not_exist(dst_roms_folder_path):
            return

        # SD:\\roms\\<plugin_name>
        dst_folder_path = os.path.join(dst_roms_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        ini_parser = ConfigParser()
        ini_parser.read(ini_file_path)
        if ini_parser.has_section(plugin_name):
            for zip_title in ini_parser[plugin_name]:
                dst_zip_path = os.path.join(
                    dst_folder_path, f"{zip_title}.zip")
                if not os.path.exists(dst_zip_path):
                    open(dst_zip_path, "w").close()

    def export_boxcovers(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not create_folder_if_not_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\boxcovers
        dst_boxcovers_folder_path = os.path.join(
            dst_wiiflow_folder_path, "boxcovers")
        if not create_folder_if_not_exist(dst_boxcovers_folder_path):
            return

        plugin_name = self.console_configs.wiiflow_plugin_name()
        # SD:\\wiiflow\\boxcovers\\<plugin_name>
        dst_folder_path = os.path.join(dst_boxcovers_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\boxcovers\\{plugin_name}")

        for zip_title in self.zip_title_to_path.keys():
            src_zip_path = os.path.join(
                src_folder_path, f"{zip_title}.zip.png")
            if os.path.exists(src_zip_path):
                dst_zip_path = os.path.join(
                    dst_folder_path, f"{zip_title}.zip.png")
                if not os.path.exists(dst_zip_path):
                    shutil.copyfile(src_zip_path, dst_zip_path)
            else:
                print(f"源文件缺失：{src_zip_path}")

    def export_cache(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not create_folder_if_not_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\cache
        dst_cache_folder_path = os.path.join(dst_wiiflow_folder_path, "cache")
        if not create_folder_if_not_exist(dst_cache_folder_path):
            return

        plugin_name = self.console_configs.wiiflow_plugin_name()
        # SD:\\wiiflow\\cache\\<plugin_name>
        dst_folder_path = os.path.join(dst_cache_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\cache\\{plugin_name}")

        for zip_title in self.zip_title_to_path.keys():
            src_file_path = os.path.join(
                src_folder_path, f"{zip_title}.zip.wfc")
            if os.path.exists(src_file_path):
                dst_file_path = os.path.join(
                    dst_folder_path, f"{zip_title}.zip.wfc")
                if not os.path.exists(dst_file_path):
                    shutil.copyfile(src_file_path, dst_file_path)
            else:
                print(f"源文件缺失：{src_file_path}")

    def export_plugins(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not create_folder_if_not_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\plugins
        dst_plugins_folder_path = os.path.join(
            dst_wiiflow_folder_path, "plugins")
        if not create_folder_if_not_exist(dst_plugins_folder_path):
            return

        # SD:\\wiiflow\\plugins\\R-Sam
        dst_rsam_folder_path = os.path.join(dst_plugins_folder_path, "R-Sam")
        if not create_folder_if_not_exist(dst_rsam_folder_path):
            return

        plugin_name = self.console_configs.wiiflow_plugin_name()
        # SD:\\wiiflow\\plugins\\R-Sam\\<plugin_name>
        dst_folder_path = os.path.join(dst_rsam_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\plugins\\R-Sam\\{plugin_name}")

        file_tuple = ("boot.dol", "config.ini", "sound.ogg")
        for file in file_tuple:
            src_file_path = os.path.join(src_folder_path, file)
            if os.path.exists(src_file_path):
                dst_file_path = os.path.join(dst_folder_path, file)
                if os.path.exists(dst_file_path):
                    os.remove(dst_file_path)
                shutil.copyfile(src_file_path, dst_file_path)
            else:
                print(f"源文件缺失：{src_file_path}")

    def export_plugins_data(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not create_folder_if_not_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\plugins_data
        dst_plugins_data_folder_path = os.path.join(
            dst_wiiflow_folder_path, "plugins_data")
        if not create_folder_if_not_exist(dst_plugins_data_folder_path):
            return

        plugin_name = self.console_configs.wiiflow_plugin_name()
        # SD:\\wiiflow\\plugins_data\\<plugin_name>
        dst_folder_path = os.path.join(
            dst_plugins_data_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\plugins_data\\{plugin_name}")

        file_tuple = (f"{plugin_name}.ini", f"{plugin_name}.xml")
        for file in file_tuple:
            src_file_path = os.path.join(src_folder_path, file)
            if os.path.exists(src_file_path):
                dst_file_path = os.path.join(dst_folder_path, file)
                if os.path.exists(dst_file_path):
                    os.remove(dst_file_path)
                shutil.copyfile(src_file_path, dst_file_path)
            else:
                print(f"源文件缺失：{src_file_path}")

    def export_snapshots(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not create_folder_if_not_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\snapshots
        dst_snapshots_folder_path = os.path.join(
            dst_wiiflow_folder_path, "snapshots")
        if not create_folder_if_not_exist(dst_snapshots_folder_path):
            return

        plugin_name = self.console_configs.wiiflow_plugin_name()
        # SD:\\wiiflow\\snapshots\\<plugin_name>
        dst_folder_path = os.path.join(dst_snapshots_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\snapshots\\{plugin_name}")

        for png_title in self.zip_title_to_path.keys():
            src_file_path = os.path.join(
                src_folder_path, f"{png_title}.png")
            if os.path.exists(src_file_path):
                dst_file_path = os.path.join(
                    dst_folder_path, f"{png_title}.png")
                if not os.path.exists(dst_file_path):
                    shutil.copyfile(src_file_path, dst_file_path)
            else:
                print(f"源文件缺失：{src_file_path}")

    def export_all(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        self.init_zip_title_to_path()
        self.export_roms()
        self.export_boxcovers()
        self.export_cache()
        self.export_plugins()
        self.export_plugins_data()
        self.export_snapshots()
