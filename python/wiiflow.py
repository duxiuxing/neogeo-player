# -- coding: UTF-8 --

import fnmatch
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


def copy_file_if_not_exist(src_file_path, dst_file_path):
    if not os.path.exists(src_file_path):
        print(f"源文件缺失：{src_file_path}")
    elif not os.path.exists(dst_file_path):
        shutil.copyfile(src_file_path, dst_file_path)


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
                        if en_title not in game_name.split(" / "):
                            print("英文名不一致")
                            print(f"\tname     = {game_name}")
                            print(f"\tEN title = {en_title}")
                    elif lang == "ZHCN":
                        zhcn_title = elem.find("title").text

            self.game_id_to_info[game_id] = GameInfo(en_title, zhcn_title)

    def find_game_info(self, zip_title, zip_crc32):
        self.init_zip_crc32_to_game_id()
        self.init_game_id_to_info()

        game_id = None
        if zip_title in self.zip_crc32_to_game_id.keys():
            game_id = self.zip_crc32_to_game_id[zip_title]
        elif zip_crc32 in self.zip_crc32_to_game_id.keys():
            game_id = self.zip_crc32_to_game_id[zip_crc32]

        if game_id is not None and game_id in self.game_id_to_info.keys():
            return self.game_id_to_info[game_id]

        print(f"{zip_title}.zip 不在 {self.console_configs.wiiflow_plugin_name()}.ini 文件中，crc32 = {zip_crc32}")
        return None

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
        dst_zip_parent_folder_path = os.path.join(
            dst_roms_folder_path, self.console_configs.wiiflow_plugin_name())
        if not create_folder_if_not_exist(dst_zip_parent_folder_path):
            return
        for zip_title, src_zip_path in self.zip_title_to_path.items():
            dst_zip_path = os.path.join(
                dst_zip_parent_folder_path, f"{zip_title}.zip")
            copy_file_if_not_exist(src_zip_path, dst_zip_path)

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

        # SD:\\fake_roms\\<plugin_name>
        dst_zip_parent_folder_path = os.path.join(
            dst_roms_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_zip_parent_folder_path):
            return

        ini_parser = ConfigParser()
        ini_parser.read(ini_file_path)
        if ini_parser.has_section(plugin_name):
            for zip_title in ini_parser[plugin_name]:
                dst_zip_path = os.path.join(
                    dst_zip_parent_folder_path, f"{zip_title}.zip")
                if not os.path.exists(dst_zip_path):
                    open(dst_zip_path, "w").close()

    def export_boxcovers(self, zip_parent_folder_path):
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
        # SD:\\wiiflow\\boxcovers\\blank_covers
        dst_blank_covers_folder_path = os.path.join(
            dst_boxcovers_folder_path, "blank_covers")
        if create_folder_if_not_exist(dst_blank_covers_folder_path):
            src_blank_cover_path = os.path.join(
                self.console_configs.folder_path(), f"wiiflow\\boxcovers\\blank_covers\\{plugin_name}.png")
            dst_blank_cover_path = os.path.join(
                dst_blank_covers_folder_path, f"{plugin_name}.png")
            copy_file_if_not_exist(src_blank_cover_path, dst_blank_cover_path)
        else:
            print(f"无效的文件夹：{dst_blank_covers_folder_path}")

        # SD:\\wiiflow\\boxcovers\\<plugin_name>
        dst_folder_path = os.path.join(dst_boxcovers_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\boxcovers\\{plugin_name}")

        for zip_file_name in os.listdir(zip_parent_folder_path):
            if not fnmatch.fnmatch(zip_file_name, "*.zip"):
                continue
            src_png_path = os.path.join(
                src_folder_path, f"{zip_file_name}.png")
            dst_png_path = os.path.join(
                dst_folder_path, f"{zip_file_name}.png")
            copy_file_if_not_exist(src_png_path, dst_png_path)

    def export_cache(self, zip_parent_folder_path):
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
        # SD:\\wiiflow\\cache\\blank_covers
        dst_cache_blank_covers_folder_path = os.path.join(
            dst_cache_folder_path, "blank_covers")
        if create_folder_if_not_exist(dst_cache_blank_covers_folder_path):
            src_cache_blank_cover_path = os.path.join(
                self.console_configs.folder_path(), f"wiiflow\\cache\\blank_covers\\{plugin_name}.wfc")
            dst_cache_blank_cover_path = os.path.join(
                dst_cache_blank_covers_folder_path, f"{plugin_name}.wfc")
            copy_file_if_not_exist(
                src_cache_blank_cover_path,         dst_cache_blank_cover_path)
        else:
            print(f"无效的文件夹：{dst_cache_blank_covers_folder_path}")

        # SD:\\wiiflow\\cache\\<plugin_name>
        dst_folder_path = os.path.join(dst_cache_folder_path, plugin_name)
        if not create_folder_if_not_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\cache\\{plugin_name}")

        for zip_file_name in os.listdir(zip_parent_folder_path):
            if not fnmatch.fnmatch(zip_file_name, "*.zip"):
                continue
            src_file_path = os.path.join(
                src_folder_path, f"{zip_file_name}.wfc")
            dst_file_path = os.path.join(
                dst_folder_path, f"{zip_file_name}.wfc")
            copy_file_if_not_exist(src_file_path, dst_file_path)

        # SD:\\wiiflow\\cache\\lists
        # lists 文件夹里都是 WiiFlow 生成的缓存文件，删掉才会重新生成
        dst_cache_lists_folder_path = os.path.join(
            dst_cache_folder_path, "lists")
        if os.path.exists(dst_cache_lists_folder_path):
            shutil.rmtree(dst_cache_lists_folder_path)

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
            dst_file_path = os.path.join(dst_folder_path, file)
            if os.path.exists(dst_file_path):
                os.remove(dst_file_path)
            copy_file_if_not_exist(src_file_path, dst_file_path)

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
            dst_file_path = os.path.join(dst_folder_path, file)
            if os.path.exists(dst_file_path):
                os.remove(dst_file_path)
            copy_file_if_not_exist(src_file_path, dst_file_path)

        # gametdb_offsets.bin 是 WiiFlow 生成的缓存文件，删掉才会重新生成
        gametdb_offsets_bin_path = os.path.join(
            dst_folder_path, "gametdb_offsets.bin")
        if os.path.exists(gametdb_offsets_bin_path):
            os.remove(gametdb_offsets_bin_path)

    def export_snapshots(self, zip_parent_folder_path):
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

        for zip_file_name in os.listdir(zip_parent_folder_path):
            if not fnmatch.fnmatch(zip_file_name, "*.zip"):
                continue
            png_title = os.path.splitext(zip_file_name)[0]
            src_file_path = os.path.join(
                src_folder_path, f"{png_title}.png")
            dst_file_path = os.path.join(
                dst_folder_path, f"{png_title}.png")
            copy_file_if_not_exist(src_file_path, dst_file_path)

    def export_source_menu(self):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not create_folder_if_not_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\source_menu
        dst_source_menu_folder_path = os.path.join(
            dst_wiiflow_folder_path, "source_menu")
        if not create_folder_if_not_exist(dst_source_menu_folder_path):
            return

        plugin_name = self.console_configs.wiiflow_plugin_name()
        src_png_path = os.path.join(
            self.console_configs.folder_path(), f"wiiflow\\source_menu\\{plugin_name}.png")
        dst_png_path = os.path.join(
            dst_source_menu_folder_path, f"{plugin_name}.png")
        copy_file_if_not_exist(src_png_path, dst_png_path)

    def export_all(self, with_fake_roms):
        if not verify_folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        zip_parent_folder_path = ""
        if with_fake_roms:
            self.export_fake_roms()
            zip_parent_folder_path = os.path.join(
                LocalConfigs.SDCARD_ROOT, f"fake_roms\\{self.console_configs.wiiflow_plugin_name()}")
        else:
            self.init_zip_title_to_path()
            self.export_roms()
            zip_parent_folder_path = os.path.join(
                LocalConfigs.SDCARD_ROOT, f"roms\\{self.console_configs.wiiflow_plugin_name()}")

        if with_fake_roms is False:
            self.export_boxcovers(zip_parent_folder_path)

        self.export_cache(zip_parent_folder_path)
        self.export_plugins()
        self.export_plugins_data()
        self.export_snapshots(zip_parent_folder_path)
        self.export_source_menu()

    def convert_game_synopsis(self):
        src_file_path = os.path.join(
            self.console_configs.folder_path(), "doc\\game_synopsis.md")

        dst_lines = []
        with open(src_file_path, "r", encoding="utf-8") as src_file:
            for line in src_file.readlines():
                src_line = line.rstrip("\n")
                if src_line.startswith("#"):
                    dst_lines.append(src_line)
                    continue
                elif len(src_line) == 0:
                    dst_lines.append("")
                    continue
                else:
                    dst_line = ""
                    for char in src_line:
                        if len(dst_line) == 0:
                            dst_line = char
                        elif dst_line[-1] in " 、：，。《》（）【】“”":
                            dst_line += char
                        elif char in " 、：，。《》（）【】“”1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            dst_line += char
                        else:
                            dst_line += f" {char}"

                    dst_lines.append(dst_line)

        dst_file_path = os.path.join(
            self.console_configs.folder_path(), "doc\\game_synopsis.wiiflow.md")
        with open(dst_file_path, "w", encoding="utf-8") as dst_file:
            for line in dst_lines:
                dst_file.write(f"{line}\n")
