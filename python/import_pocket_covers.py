# -- coding: UTF-8 --

import fnmatch
import os

from console import Console
from main_menu import CmdHandler
from main_menu import MainMenu

from PIL import Image


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


class ImportPocketCovers(CmdHandler):
    def __init__(self):
        super().__init__("WiiFlow - 导入 - boxcovers_import 文件夹里的非标准封面")
        # 已经导入过的封面文件名列表，避免重复导入
        self.file_names_imported = []

    def import_folder_path(self):
        return os.path.join(MainMenu.console.root_folder_path(),
                            "wiiflow\\boxcovers_import")

    def blank_cover(self):
        plugin_name = MainMenu.console.wiiflow().plugin_name()
        cover_path = os.path.join(MainMenu.console.root_folder_path(),
                                  f"wiiflow\\boxcovers\\blank_covers\\{plugin_name}.png")
        cover = Image.open(cover_path)
        if cover.width != 1090 or cover.height != 458:
            print(f"standard_cover error: {cover.width} x {cover.height}")
            print(f"standard_cover path: {cover_path}")
            return None
        else:
            return cover

    def save_wiiflow_boxcover(self, rom_title, image):
        plugin_name = MainMenu.console.wiiflow().plugin_name()
        file_path = os.path.join(
            MainMenu.console.root_folder_path(),
            f"wiiflow\\boxcovers\\{plugin_name}\\{rom_title}{MainMenu.console.rom_extension()}.png")
        if os.path.exists(file_path):
            os.remove(file_path)
        image.save(file_path)

        file_path = os.path.join(
            MainMenu.console.root_folder_path(),
            f"wiiflow\\cache\\{plugin_name}\\{rom_title}{MainMenu.console.rom_extension()}.wfc")
        if os.path.exists(file_path):
            os.remove(file_path)

    def combine_front_and_back_cover(self, file_title):
        blank_cover = self.blank_cover()
        if blank_cover is None:
            return

        x1 = 514
        x2 = 578
        x3 = 672

        back_file_name = f"{file_title}.back.png"
        back_file_path = os.path.join(
            self.import_folder_path(), back_file_name)
        if os.path.exists(back_file_path):
            back_image = Image.open(back_file_path).resize(
                (x1, blank_cover.height))
            blank_cover.paste(back_image, (0, 0))
            self.file_names_imported.append(back_file_name)
        else:
            print(f"封底文件缺失：{back_file_path}")

        front_file_name = f"{file_title}.front.png"
        front_file_path = os.path.join(
            self.import_folder_path(), front_file_name)
        if os.path.exists(front_file_path):
            front_image = Image.open(front_file_path).resize(
                (blank_cover.width - x3, blank_cover.height))
            blank_cover.paste(front_image, (x3, 0))
            self.file_names_imported.append(front_file_name)
        else:
            print(f"封面文件缺失：{front_file_path}")

        logo_file_name = f"{file_title}.logo.png"
        logo_file_path = os.path.join(
            self.import_folder_path(), logo_file_name)
        if os.path.exists(logo_file_path):
            logo_image = Image.open(logo_file_path).resize(
                (x2 - x1, blank_cover.height))
            blank_cover.paste(logo_image, (x1, 0))
            self.file_names_imported.append(logo_file_name)
        else:
            print(f"标题文件缺失：{logo_file_name}")

        self.save_wiiflow_boxcover(file_title, blank_cover)

    def import_cover_1090x458(self, file_title, cover_1090x458):
        blank_cover = self.blank_cover()
        if blank_cover is None:
            return

        x1 = 514
        x2 = 672

        back_box = [0, 0, x1, cover_1090x458.height]
        back_crop = cover_1090x458.crop(back_box)

        front_box = [x2, 0, cover_1090x458.width, cover_1090x458.height]
        front_crop = cover_1090x458.crop(front_box)

        blank_cover.paste(back_crop, (0, 0))
        blank_cover.paste(front_crop, (x2, 0))

        self.save_wiiflow_boxcover(file_title, blank_cover)

    def run(self):
        if not folder_exist(self.import_folder_path()):
            return

        for file_name in os.listdir(self.import_folder_path()):
            if not fnmatch.fnmatch(file_name, "*.png"):
                continue

            if file_name in self.file_names_imported:
                continue

            file_title = os.path.splitext(file_name)[0]
            if file_name.endswith(".back.png") or file_name.endswith(".front.png") or file_name.endswith(".logo.png"):
                file_title = os.path.splitext(file_title)[0]
                self.combine_front_and_back_cover(file_title)
            else:
                file_path = os.path.join(
                    self.import_folder_path(), file_name)
                image = Image.open(file_path)
                if image.width == 1090 and image.height == 458:
                    self.import_cover_1090x458(file_title, image)
                else:
                    print(f"cover error: {file_path}")
