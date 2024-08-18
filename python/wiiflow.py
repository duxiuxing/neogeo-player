# -- coding: UTF-8 --

import fnmatch
import os
import shutil
import subprocess
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
    def __init__(self, console, plugin_name):
        self.console = console

        # 机种对应的 WiiFlow 插件名称
        self.plugin_name = plugin_name

        # CRC32 值和 .zip 文件标题为键，游戏 ID 为值的字典
        # 内容来自 <self.plugin_name>.ini
        # 读取操作在 self.init_rom_crc32_to_game_id() 中实现
        self.rom_crc32_to_game_id = {}

        # 游戏 ID 为键，GameInfo 为值的字典
        # 内容来自 <self.plugin_name>.xml
        # 读取操作在 self.init_game_id_to_info() 中实现
        self.game_id_to_info = {}

        # .zip 文件标题为键，.zip 文件路径为值的字典
        # 内容来自 wiiflow\\roms.xml，其实就是所有 WiiFlow 用的 .zip 文件
        # 读取操作在 self.init_rom_name_to_path() 中实现
        self.rom_name_to_path = {}

    def init_rom_crc32_to_game_id(self):
        # 本函数执行的操作如下：
        # 1. 读取 <self.plugin_name>.ini
        # 2. 填充 self.rom_crc32_to_game_id
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
                    if self.game_id_to_info[game_id].en_title != rom_title:
                        print("ROM 文件标题和游戏英文名不一致")
                        print(f"\t{rom_title} 在 .ini")
                        print(
                            f"\t{self.game_id_to_info[game_id].en_title} 在 .xml")
                    self.game_id_to_info[game_id].rom_name = f"{rom_title}{self.console.rom_extension()}"
                for index in range(1, len(values)):
                    rom_crc32 = values[index].rjust(8, "0")
                    self.rom_crc32_to_game_id[rom_crc32] = game_id

    def init_game_id_to_info(self):
        # 本函数执行的操作如下：
        # 1. 读取 <self.plugin_name>.xml
        # 2. 填充 self.game_id_to_info
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

    def find_game_info(self, rom_title, rom_crc32):
        # 根据 CRC32 值或 ROM 文件标题查找 GameInfo
        # Args:
        #     rom_title (str): ROM 文件的标题，比如 1941.zip 的标题就是 1941
        #     rom_crc32 (str): ROM 文件的 CRC32 值
        # Returns:
        #     找到则返回 GameInfo 对象，否则返回 None
        self.init_game_id_to_info()
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

    def init_rom_name_to_path(self):
        # 本函数执行的操作如下：
        # 1. 读取 wiiflow\\roms.xml
        # 2. 填充 self.rom_name_to_path
        # 3. 有防止重复读取的逻辑
        if len(self.rom_name_to_path) > 0:
            return

        xml_file_path = os.path.join(
            self.console.root_folder_path(), "wiiflow\\roms.xml")

        if not os.path.exists(xml_file_path):
            print(f"无效的文件：{xml_file_path}")
            return

        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        for game_elem in root.findall("Game"):
            rom_crc32 = game_elem.get("crc32").rjust(8, "0")
            rom_name = game_elem.get("rom")
            if rom_name == None:
                rom_name = game_elem.get("zip") + ".zip"
            if rom_name is None:
                print(f"crc32 = {rom_crc32} 的元素缺少 rom/zip 属性")
                continue
            rom_path = os.path.join(
                self.console.root_folder_path(), f"roms\\{rom_name}")
            if not os.path.exists(rom_path):
                rom_title = os.path.splitext(rom_name)[0]
                rom_extension = os.path.splitext(rom_name)[1]
                rom_path = os.path.join(
                    self.console.root_folder_path(), f"roms\\{rom_title}\\{rom_crc32}{rom_extension}")
                if not os.path.exists(rom_path):
                    print(f"无效的文件：{rom_path}")
                    continue

            self.rom_name_to_path[rom_name] = rom_path

    def convert_wfc_files(self):
        # 调用 wfc_conv.exe 生成 WiiFlow 专用的游戏封面文件（.png 格式转 .wfc 格式）
        # .wfc 格式的文件都存放在 wiiflow\\cache 文件夹里
        if not os.path.exists(LocalConfigs.wfc_conv_exe_path()):
            print(f"无效的文件：{LocalConfigs.wfc_conv_exe_path()}")
            zip_file_path = os.path.join(
                LocalConfigs.repository_folder_path(), "pc-tool\\WFC_conv_0-1.zip")
            print(f"安装文件在 {zip_file_path}")
            return

        # wiiflow
        wiiflow_foler_path = os.path.join(
            self.console.root_folder_path(), "wiiflow")
        if not verify_folder_exist(wiiflow_foler_path):
            print(f"无效文件夹：{wiiflow_foler_path}")
            return

        # wiiflow\\cache
        cache_folder_path = os.path.join(wiiflow_foler_path, "cache")
        if not verify_folder_exist(cache_folder_path):
            print(f"无效文件夹：{cache_folder_path}")
            return

        cmd_line = f"\"{LocalConfigs.wfc_conv_exe_path()}\" \"{wiiflow_foler_path}\""
        print(cmd_line)
        subprocess.call(cmd_line)

    def export_roms(self):
        # 本函数用于把 self.rom_name_to_path 所有的 .zip 文件导出到 Wii 的 SD 卡
        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\roms
        dst_roms_folder_path = os.path.join(LocalConfigs.sd_path(), "roms")
        if not verify_folder_exist(dst_roms_folder_path):
            return

        # SD:\\roms\\<plugin_name>
        roms_plugin_name_folder_path = os.path.join(
            dst_roms_folder_path, self.plugin_name)
        if not verify_folder_exist(roms_plugin_name_folder_path):
            return

        self.init_rom_name_to_path()
        for rom_name, src_rom_path in self.rom_name_to_path.items():
            rom_title = os.path.splitext(rom_name)[0]
            rom_extension = os.path.splitext(rom_name)[1]
            dst_rom_path = os.path.join(
                roms_plugin_name_folder_path, f"{rom_name}")
            copy_file_if_not_exist(src_rom_path, dst_rom_path)

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
        if ini_parser.has_section(self.plugin_name):
            for rom_title in ini_parser[self.plugin_name]:
                dst_zip_path = os.path.join(
                    roms_plugin_name_folder_path, f"{rom_title}{self.console.rom_extension()}")
                if not os.path.exists(dst_zip_path):
                    open(dst_zip_path, "w").close()

    def export_png_boxcovers(self):
        # 本函数执行的操作如下：
        # 1. 把 wiiflow\\boxcovers\\blank_covers 里的默认封面文件（.png 格式）导出到 Wii 的 SD 卡
        # 2. 根据 SD 卡里的 ROM 文件，把对应的封面文件（.png 格式）导出到 Wii 的 SD 卡
        #
        # 注意：WiiFlow 中展示的游戏封面对应于 cache 文件夹里的 .wfc 文件，如果已经导出过 .wfc 格式的封面文件，可以不导出 .png 格式的
        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.sd_path(), "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\boxcovers
        dst_boxcovers_folder_path = os.path.join(
            dst_wiiflow_folder_path, "boxcovers")
        if not verify_folder_exist(dst_boxcovers_folder_path):
            return

        # SD:\\wiiflow\\boxcovers\\blank_covers
        src_blank_cover_path = os.path.join(
            self.console.root_folder_path(),
            f"wiiflow\\boxcovers\\blank_covers\\{self.plugin_name}.png")
        if os.path.exists(src_blank_cover_path):
            dst_blank_covers_folder_path = os.path.join(
                dst_boxcovers_folder_path, "blank_covers")
            if verify_folder_exist(dst_blank_covers_folder_path):
                dst_blank_cover_path = os.path.join(
                    dst_blank_covers_folder_path, f"{self.plugin_name}.png")
                copy_file_if_not_exist(
                    src_blank_cover_path, dst_blank_cover_path)

        # SD:\\wiiflow\\boxcovers\\<plugin_name>
        dst_folder_path = os.path.join(
            dst_boxcovers_folder_path, self.plugin_name)
        if not verify_folder_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console.root_folder_path(), f"wiiflow\\boxcovers\\{self.plugin_name}")

        roms_plugin_name_folder_path = os.path.join(
            LocalConfigs.sd_path(), f"roms\\{self.plugin_name}")
        for rom_name in os.listdir(roms_plugin_name_folder_path):
            if not self.console.rom_extension_match(rom_name):
                continue
            src_png_path = os.path.join(
                src_folder_path, f"{rom_name}.png")
            dst_png_path = os.path.join(
                dst_folder_path, f"{rom_name}.png")
            copy_file_if_not_exist(src_png_path, dst_png_path)

    def export_cache(self):
        # 本函数执行的操作如下：
        # 1. 把 wiiflow\\cache\\blank_covers 里的默认封面文件（.wfc 格式）导出到 Wii 的 SD 卡
        # 2. 根据 SD 卡里的 ROM 文件，把对应的封面文件（.wfc 格式）导出到 Wii 的 SD 卡
        # 3. 删除 SD:\\wiiflow\\cache 里可能失效的缓存文件
        #
        # 注意：WiiFlow 中展示的游戏封面对应于 cache 文件夹里的 .wfc 文件，如果导出了 .wfc 格式的封面文件，可以不导出 .png 格式的
        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.sd_path(), "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\cache
        dst_cache_folder_path = os.path.join(dst_wiiflow_folder_path, "cache")
        if not verify_folder_exist(dst_cache_folder_path):
            return

        # SD:\\wiiflow\\cache\\blank_covers
        src_cache_blank_cover_path = os.path.join(
            self.console.root_folder_path(),
            f"wiiflow\\cache\\blank_covers\\{self.plugin_name}.wfc")
        if os.path.exists(src_cache_blank_cover_path):
            dst_cache_blank_covers_folder_path = os.path.join(
                dst_cache_folder_path, "blank_covers")
            if verify_folder_exist(dst_cache_blank_covers_folder_path):
                dst_cache_blank_cover_path = os.path.join(
                    dst_cache_blank_covers_folder_path, f"{self.plugin_name}.wfc")
                copy_file_if_not_exist(
                    src_cache_blank_cover_path, dst_cache_blank_cover_path)

        # SD:\\wiiflow\\cache\\<plugin_name>
        dst_folder_path = os.path.join(dst_cache_folder_path, self.plugin_name)
        if not verify_folder_exist(dst_folder_path):
            return

        src_folder_path = os.path.join(
            self.console.root_folder_path(), f"wiiflow\\cache\\{self.plugin_name}")

        roms_plugin_name_folder_path = os.path.join(
            LocalConfigs.sd_path(), f"roms\\{self.plugin_name}")
        for rom_name in os.listdir(roms_plugin_name_folder_path):
            if not self.console.rom_extension_match(rom_name):
                continue
            src_file_path = os.path.join(
                src_folder_path, f"{rom_name}.wfc")
            dst_file_path = os.path.join(
                dst_folder_path, f"{rom_name}.wfc")
            copy_file_if_not_exist(src_file_path, dst_file_path)

        # SD:\\wiiflow\\cache\\lists
        # lists 文件夹里都是 WiiFlow 生成的缓存文件，删掉才会重新生成
        dst_cache_lists_folder_path = os.path.join(
            dst_cache_folder_path, "lists")
        if os.path.exists(dst_cache_lists_folder_path):
            shutil.rmtree(dst_cache_lists_folder_path)

    def export_plugin(self):
        # 本函数用于把 wiiflow\\plugins 里的文件导出到 Wii 的 SD 卡
        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.sd_path(), "wiiflow")
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
            self.console.root_folder_path(), f"wiiflow\\plugins\\R-Sam\\{self.plugin_name}")

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
        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.sd_path(), "wiiflow")
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
            self.console.root_folder_path(), f"wiiflow\\plugins_data\\{self.plugin_name}")

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
        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.sd_path(), "wiiflow")
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
            self.console.root_folder_path(), f"wiiflow\\snapshots\\{self.plugin_name}")

        roms_plugin_name_folder_path = os.path.join(
            LocalConfigs.sd_path(), f"roms\\{self.plugin_name}")
        for rom_name in os.listdir(roms_plugin_name_folder_path):
            if not self.console.rom_extension_match(rom_name):
                continue
            png_title = os.path.splitext(rom_name)[0]
            src_file_path = os.path.join(
                src_folder_path, f"{png_title}.png")
            dst_file_path = os.path.join(
                dst_folder_path, f"{png_title}.png")
            copy_file_if_not_exist(src_file_path, dst_file_path)

    def export_source_menu(self):
        # 本函数用于把 wiiflow\\source_menu 里的源菜单图标（.png格式）导出到 Wii 的 SD 卡
        if not folder_exist(LocalConfigs.sd_path()):
            return

        # SD:\\wiiflow
        dst_wiiflow_folder_path = os.path.join(
            LocalConfigs.sd_path(), "wiiflow")
        if not verify_folder_exist(dst_wiiflow_folder_path):
            return

        # SD:\\wiiflow\\source_menu
        dst_source_menu_folder_path = os.path.join(
            dst_wiiflow_folder_path, "source_menu")
        if not verify_folder_exist(dst_source_menu_folder_path):
            return

        src_png_path = os.path.join(
            self.console.root_folder_path(), f"wiiflow\\source_menu\\{self.plugin_name}.png")
        dst_png_path = os.path.join(
            dst_source_menu_folder_path, f"{self.plugin_name}.png")
        copy_file_if_not_exist(src_png_path, dst_png_path)

    def convert_game_synopsis(self):
        # wiiflow\\plugins_data 里的 <self.plugin_name>.xml 可以配置游戏的中文摘要
        # 但 WiiFlow 在显示中文句子的时候不会自动换行，需要在每个汉字之间加上空格才能有较好的显示效果，
        # 本函数用于生成 WiiFlow 专用排版格式的游戏摘要文本，原始的摘要文本存于 game_synopsis.md，
        # 转换后的摘要文本存于 game_synopsis.wiiflow.md，需要手动合入 <self.plugin_name>.xml
        src_file_path = os.path.join(
            self.console.root_folder_path(), "doc\\game_synopsis.md")
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
            self.console.root_folder_path(), "doc\\game_synopsis.wiiflow.md")
        with open(dst_file_path, "w", encoding="utf-8") as dst_file:
            for line in dst_lines:
                dst_file.write(f"{line}\n")
