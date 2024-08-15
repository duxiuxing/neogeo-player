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
        return os.path.isdir(folder_path)


def copy_file_if_not_exist(src_file_path, dst_file_path):
    # 复制源文件到目标路径，如果目标文件已存在则跳过
    # Args:
    #     src_file_path (str): 源文件路径
    #     dst_file_path (str): 目标文件路径
    if not os.path.exists(src_file_path):
        print(f"源文件缺失：{src_file_path}")
    elif not os.path.exists(dst_file_path):
        shutil.copyfile(src_file_path, dst_file_path)


class WiiFlow:
    def __init__(self, console_config, plugin_name):
        # 机种对应的文件夹路径
        self.console_root_folder_path = console_config.root_folder_path()

        # 机种对应的 WiiFlow 插件名称
        self.plugin_name = plugin_name

        # CRC32 值和 .zip 文件标题为键，游戏 ID 为值的字典
        # 内容来自 <self.plugin_name>.ini
        # 读取操作在 self.init_zip_crc32_to_game_id() 中实现
        self.zip_crc32_to_game_id = {}

        # 游戏 ID 为键，GameInfo 为值的字典
        # 内容来自 <self.plugin_name>.xml
        # 读取操作在 self.init_game_id_to_info() 中实现
        self.game_id_to_info = {}

        # .zip 文件标题为键，.zip 文件路径为值的字典
        # 内容来自 wiiflow\\roms.xml，其实就是所有 WiiFlow 用的 .zip 文件
        # 读取操作在 self.init_zip_title_to_path() 中实现
        self.zip_title_to_path = {}

    def init_zip_crc32_to_game_id(self):
        # 本函数执行的操作如下：
        # 1. 读取 <self.plugin_name>.ini
        # 2. 填充 self.zip_crc32_to_game_id
        # 3. 有防止重复读取的逻辑
        if len(self.zip_crc32_to_game_id) > 0:
            return

        ini_file_path = os.path.join(
            self.console_root_folder_path,
            f"wiiflow\\plugins_data\\{self.plugin_name}\\{self.plugin_name}.ini")

        if not os.path.exists(ini_file_path):
            print(f"无效的文件：{ini_file_path}")
            return

        ini_parser = ConfigParser()
        ini_parser.read(ini_file_path)
        if ini_parser.has_section(self.plugin_name):
            for zip_title in ini_parser[self.plugin_name]:
                values = ini_parser[self.plugin_name][zip_title].split("|")
                game_id = values[0]
                self.zip_crc32_to_game_id[zip_title] = game_id
                for index in range(1, len(values)):
                    self.zip_crc32_to_game_id[values[index].rjust(
                        8, "0")] = game_id

    def init_game_id_to_info(self):
        # 本函数执行的操作如下：
        # 1. 读取 <self.plugin_name>.xml
        # 2. 填充 self.game_id_to_info
        # 3. 有防止重复读取的逻辑
        if len(self.game_id_to_info) > 0:
            return

        xml_file_path = os.path.join(
            self.console_root_folder_path,
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

    def find_game_info(self, zip_title, zip_crc32):
        # 根据 CRC32 值或 .zip 文件标题查找 GameInfo
        # Args:
        #     zip_title (str): .zip 文件的标题，比如 1941.zip 的标题就是 1941
        #     zip_crc32 (str): .zip 文件的 CRC32 值
        # Returns:
        #     找到则返回 GameInfo 对象，否则返回 None
        self.init_zip_crc32_to_game_id()
        self.init_game_id_to_info()

        game_id = None
        if zip_title in self.zip_crc32_to_game_id.keys():
            game_id = self.zip_crc32_to_game_id[zip_title]
        elif zip_crc32 in self.zip_crc32_to_game_id.keys():
            game_id = self.zip_crc32_to_game_id[zip_crc32]

        if game_id is not None and game_id in self.game_id_to_info.keys():
            return self.game_id_to_info[game_id]

        print(f"{zip_title}.zip 不在 {self.plugin_name}.ini 中，crc32 = {zip_crc32}")
        return None

    def init_zip_title_to_path(self):
        # 本函数执行的操作如下：
        # 1. 读取 wiiflow\\roms.xml
        # 2. 填充 self.zip_title_to_path
        # 3. 有防止重复读取的逻辑
        if len(self.zip_title_to_path) > 0:
            return

        xml_file_path = os.path.join(
            self.console_root_folder_path, "wiiflow\\roms.xml")

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
                self.console_root_folder_path, f"roms\\{zip_title}.zip")
            if not os.path.exists(zip_path):
                zip_path = os.path.join(
                    self.console_root_folder_path, f"roms\\{zip_title}\\{zip_crc32}.zip")
                if not os.path.exists(zip_path):
                    print(f"无效的文件：{zip_path}")
                    continue

            self.zip_title_to_path[zip_title] = zip_path

    def convert_wfc_files(self):
        # 调用 wfc_conv.exe 把 wiiflow 文件夹里的图片文件（主要是游戏封面）转换成 .wfc 格式
        # .wfc 格式的图片文件都在 wiiflow\\cache 文件夹里，，目的是为了提高读取速度
        if not os.path.exists(LocalConfigs.WFC_CONV_EXE):
            print(f"无效的文件：{LocalConfigs.WFC_CONV_EXE}")
            zip_file_path = os.path.join(
                LocalConfigs.REPOSITORY_FOLDER, "pc-tool\\WFC_conv_0-1.zip")
            print(f"安装文件在 {zip_file_path}")
            return

        # wiiflow
        wiiflow_foler_path = os.path.join(
            self.console_root_folder_path, "wiiflow")
        if not verify_folder_exist(wiiflow_foler_path):
            print(f"无效文件夹：{wiiflow_foler_path}")
            return

        # wiiflow\\cache
        cache_folder_path = os.path.join(wiiflow_foler_path, "cache")
        if not verify_folder_exist(cache_folder_path):
            print(f"无效文件夹：{cache_folder_path}")
            return

        cmd_line = f"\"{LocalConfigs.WFC_CONV_EXE}\" \"{wiiflow_foler_path}\""
        print(cmd_line)
        subprocess.call(cmd_line)

    def export_roms(self):
        # 本函数用于把 self.zip_title_to_path 所有的 .zip 文件导出到 Wii 的 SD 卡
        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\roms
        dst_roms_folder_path = os.path.join(LocalConfigs.SDCARD_ROOT, "roms")
        if not verify_folder_exist(dst_roms_folder_path):
            return

        # SD:\\roms\\<plugin_name>
        roms_plugin_name_folder_path = os.path.join(
            dst_roms_folder_path, self.plugin_name)
        if not verify_folder_exist(roms_plugin_name_folder_path):
            return

        self.init_zip_title_to_path()
        for zip_title, src_zip_path in self.zip_title_to_path.items():
            dst_zip_path = os.path.join(
                roms_plugin_name_folder_path, f"{zip_title}.zip")
            copy_file_if_not_exist(src_zip_path, dst_zip_path)

    def export_fake_roms(self):
        # 本函数会根据 <plugin_name>.ini 创建空白的 .zip 文件并导出到 Wii 的 SD 卡
        # 主要是为了方便在 WiiFlow 中展示所有游戏封面，而不需要在 SD 卡里装上所有游戏
        ini_file_path = os.path.join(
            self.console_root_folder_path,
            f"wiiflow\\plugins_data\\{self.plugin_name}\\{self.plugin_name}.ini")

        if not os.path.exists(ini_file_path):
            print(f"无效的文件：{ini_file_path}")
            return

        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\roms
        dst_roms_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "roms")
        if not verify_folder_exist(dst_roms_folder_path):
            return

        # SD:\\roms\\<plugin_name>
        roms_plugin_name_folder_path = os.path.join(
            dst_roms_folder_path, self.plugin_name)
        if not verify_folder_exist(roms_plugin_name_folder_path):
            return

        ini_parser = ConfigParser()
        ini_parser.read(ini_file_path)
        if ini_parser.has_section(self.plugin_name):
            for zip_title in ini_parser[self.plugin_name]:
                dst_zip_path = os.path.join(
                    roms_plugin_name_folder_path, f"{zip_title}.zip")
                if not os.path.exists(dst_zip_path):
                    open(dst_zip_path, "w").close()

    def export_png_boxcovers(self):
        # 本函数执行的操作如下：
        # 1. 把 wiiflow\\boxcovers\\blank_covers 里的默认封面文件（.png 格式）导出到 Wii 的 SD 卡
        # 2. 根据 SD 卡里的 ROM 文件，把对应的封面文件（.png 格式）导出到 Wii 的 SD 卡
        #
        # 注意：WiiFlow 中展示的游戏封面对应于 cache 文件夹里的 .wfc 文件，如果已经导出过 .wfc 格式的封面文件，可以不导出 .png 格式的
        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\boxcovers
        dst_boxcovers_folder_path = os.path.join(
            dst_wiiflow_folder_path, "boxcovers")
        if not verify_folder_exist(dst_boxcovers_folder_path):
            return

        # SD:\\wiiflow\\boxcovers\\blank_covers
        dst_blank_covers_folder_path = os.path.join(
            dst_boxcovers_folder_path, "blank_covers")
        if verify_folder_exist(dst_blank_covers_folder_path):
            src_blank_cover_path = os.path.join(
                self.console_root_folder_path, f"wiiflow\\boxcovers\\blank_covers\\{self.plugin_name}.png")
            dst_blank_cover_path = os.path.join(
                dst_blank_covers_folder_path, f"{self.plugin_name}.png")
            copy_file_if_not_exist(src_blank_cover_path, dst_blank_cover_path)
        else:
            print(f"无效的文件夹：{dst_blank_covers_folder_path}")

        # SD:\\wiiflow\\boxcovers\\<plugin_name>
        dst_folder_path = os.path.join(
            dst_boxcovers_folder_path, self.plugin_name)
        if not verify_folder_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_root_folder_path, f"wiiflow\\boxcovers\\{self.plugin_name}")

        roms_plugin_name_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, f"roms\\{self.plugin_name}")
        for zip_name in os.listdir(roms_plugin_name_folder_path):
            if not fnmatch.fnmatch(zip_name, "*.zip"):
                continue
            src_png_path = os.path.join(
                src_folder_path, f"{zip_name}.png")
            dst_png_path = os.path.join(
                dst_folder_path, f"{zip_name}.png")
            copy_file_if_not_exist(src_png_path, dst_png_path)

    def export_cache(self):
        # 本函数执行的操作如下：
        # 1. 把 wiiflow\\cache\\blank_covers 里的默认封面文件（.wfc 格式）导出到 Wii 的 SD 卡
        # 2. 根据 SD 卡里的 ROM 文件，把对应的封面文件（.wfc 格式）导出到 Wii 的 SD 卡
        # 3. 删除 SD:\\wiiflow\\cache 里可能失效的缓存文件
        #
        # 注意：WiiFlow 中展示的游戏封面对应于 cache 文件夹里的 .wfc 文件，如果导出了 .wfc 格式的封面文件，可以不导出 .png 格式的
        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\cache
        dst_cache_folder_path = os.path.join(dst_wiiflow_folder_path, "cache")
        if not verify_folder_exist(dst_cache_folder_path):
            return

        # SD:\\wiiflow\\cache\\blank_covers
        dst_cache_blank_covers_folder_path = os.path.join(
            dst_cache_folder_path, "blank_covers")
        if verify_folder_exist(dst_cache_blank_covers_folder_path):
            src_cache_blank_cover_path = os.path.join(
                self.console_root_folder_path, f"wiiflow\\cache\\blank_covers\\{self.plugin_name}.wfc")
            dst_cache_blank_cover_path = os.path.join(
                dst_cache_blank_covers_folder_path, f"{self.plugin_name}.wfc")
            copy_file_if_not_exist(
                src_cache_blank_cover_path,
                dst_cache_blank_cover_path)
        else:
            print(f"无效的文件夹：{dst_cache_blank_covers_folder_path}")

        # SD:\\wiiflow\\cache\\<plugin_name>
        dst_folder_path = os.path.join(dst_cache_folder_path, self.plugin_name)
        if not verify_folder_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_root_folder_path, f"wiiflow\\cache\\{self.plugin_name}")

        roms_plugin_name_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, f"roms\\{self.plugin_name}")
        for zip_name in os.listdir(roms_plugin_name_folder_path):
            if not fnmatch.fnmatch(zip_name, "*.zip"):
                continue
            src_file_path = os.path.join(
                src_folder_path, f"{zip_name}.wfc")
            dst_file_path = os.path.join(
                dst_folder_path, f"{zip_name}.wfc")
            copy_file_if_not_exist(src_file_path, dst_file_path)

        # SD:\\wiiflow\\cache\\lists
        # lists 文件夹里都是 WiiFlow 生成的缓存文件，删掉才会重新生成
        dst_cache_lists_folder_path = os.path.join(
            dst_cache_folder_path, "lists")
        if os.path.exists(dst_cache_lists_folder_path):
            shutil.rmtree(dst_cache_lists_folder_path)

    def export_plugin(self):
        # 本函数用于把 wiiflow\\plugins 里的文件导出到 Wii 的 SD 卡
        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\plugins
        dst_plugins_folder_path = os.path.join(
            dst_wiiflow_folder_path, "plugins")
        if not verify_folder_exist(dst_plugins_folder_path):
            return

        # SD:\\wiiflow\\plugins\\R-Sam
        dst_rsam_folder_path = os.path.join(dst_plugins_folder_path, "R-Sam")
        if not verify_folder_exist(dst_rsam_folder_path):
            return

        # SD:\\wiiflow\\plugins\\R-Sam\\<plugin_name>
        dst_folder_path = os.path.join(dst_rsam_folder_path, self.plugin_name)
        if not verify_folder_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_root_folder_path, f"wiiflow\\plugins\\R-Sam\\{self.plugin_name}")

        file_tuple = ("boot.dol", "config.ini", "sound.ogg")
        for file in file_tuple:
            src_file_path = os.path.join(src_folder_path, file)
            dst_file_path = os.path.join(dst_folder_path, file)
            if os.path.exists(dst_file_path):
                os.remove(dst_file_path)
            copy_file_if_not_exist(src_file_path, dst_file_path)

    def export_plugins_data(self):
        # # 本函数执行的操作如下：
        # 1. 把 wiiflow\\plugins_data 里的文件导出到 Wii 的 SD 卡
        # 2. 删除可能失效的缓存文件：gametdb_offsets.bin
        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\plugins_data
        dst_plugins_data_folder_path = os.path.join(
            dst_wiiflow_folder_path, "plugins_data")
        if not verify_folder_exist(dst_plugins_data_folder_path):
            return

        # SD:\\wiiflow\\plugins_data\\<plugin_name>
        dst_folder_path = os.path.join(
            dst_plugins_data_folder_path, self.plugin_name)
        if not verify_folder_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_root_folder_path, f"wiiflow\\plugins_data\\{self.plugin_name}")

        file_tuple = (f"{self.plugin_name}.ini", f"{self.plugin_name}.xml")
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

    def export_snapshots(self):
        # 本函数用于把 wiiflow\\snapshots 里的游戏截图（.png格式）导出到 Wii 的 SD 卡
        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\snapshots
        dst_snapshots_folder_path = os.path.join(
            dst_wiiflow_folder_path, "snapshots")
        if not verify_folder_exist(dst_snapshots_folder_path):
            return

        # SD:\\wiiflow\\snapshots\\<plugin_name>
        dst_folder_path = os.path.join(
            dst_snapshots_folder_path, self.plugin_name)
        if not verify_folder_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console_root_folder_path, f"wiiflow\\snapshots\\{self.plugin_name}")

        roms_plugin_name_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, f"roms\\{self.plugin_name}")
        for zip_file_name in os.listdir(roms_plugin_name_folder_path):
            if not fnmatch.fnmatch(zip_file_name, "*.zip"):
                continue
            png_title = os.path.splitext(zip_file_name)[0]
            src_file_path = os.path.join(
                src_folder_path, f"{png_title}.png")
            dst_file_path = os.path.join(
                dst_folder_path, f"{png_title}.png")
            copy_file_if_not_exist(src_file_path, dst_file_path)

    def export_source_menu(self):
        # 本函数用于把 wiiflow\\source_menu 里的源菜单图标（.png格式）导出到 Wii 的 SD 卡
        if not folder_exist(LocalConfigs.SDCARD_ROOT):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.SDCARD_ROOT, "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\source_menu
        dst_source_menu_folder_path = os.path.join(
            dst_wiiflow_folder_path, "source_menu")
        if not verify_folder_exist(dst_source_menu_folder_path):
            return

        src_png_path = os.path.join(
            self.console_root_folder_path, f"wiiflow\\source_menu\\{self.plugin_name}.png")
        dst_png_path = os.path.join(
            dst_source_menu_folder_path, f"{self.plugin_name}.png")
        copy_file_if_not_exist(src_png_path, dst_png_path)

    def convert_game_synopsis(self):
        # wiiflow\\plugins_data 里的 <self.plugin_name>.xml 里可以配置游戏的中文摘要
        # 但 WiiFlow 在显示中文句子的时候不会自动换行，需要在每个汉字之间加上空格才能有较好的显示效果，
        # 本函数用于把 game_synopsis.md 中的摘要文本转换成 WiiFlow 需要的排版格式
        # 转换后的摘要文本存于 game_synopsis.wiiflow.md，需要手动合入 <self.plugin_name>.xml
        src_file_path = os.path.join(
            self.console_root_folder_path, "doc\\game_synopsis.md")
        if not os.path.exists(src_file_path):
            return

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
            self.console_root_folder_path, "doc\\game_synopsis.wiiflow.md")
        with open(dst_file_path, "w", encoding="utf-8") as dst_file:
            for line in dst_lines:
                dst_file.write(f"{line}\n")
