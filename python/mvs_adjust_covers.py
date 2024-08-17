# -- coding: UTF-8 --

import os
import shutil

from console import Console
from local_configs import LocalConfigs
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


class AdjustCovers(CmdHandler):
    def __init__(self):
        super().__init__("NeoGeoMVS - 导入 - adjust_covers 文件夹里的非标准封面")
        # 已经调整过的封面文件名列表，避免重复调整
        self.file_names_adjusted = []

    def adjust_covers_folder_path(self):
        return os.path.join(MainMenu.console.root_folder_path(), "adjust_covers")

    def standard_cover_path(self):
        return os.path.join(MainMenu.console.root_folder_path(), "wiiflow\\boxcovers\\blank_covers\\NEOGEO.png")

    def save_wiiflow_boxcover(self, zip_title, image):
        file_path = os.path.join(
            MainMenu.console.root_folder_path(),
            f"wiiflow\\boxcovers\\NEOGEO\\{zip_title}.zip.png")
        if os.path.exists(file_path):
            os.remove(file_path)
        image.save(file_path)

        file_path = os.path.join(
            MainMenu.console.root_folder_path(),
            f"wiiflow\\cache\\NEOGEO\\{zip_title}.zip.wfc")
        if os.path.exists(file_path):
            os.remove(file_path)

    def combine_front_and_back_cover(self, file_title):
        cover_1090x680 = Image.open(self.standard_cover_path())
        if cover_1090x680.width != 1090 or cover_1090x680.height != 680:
            print(
                f"standard_cover error: {cover_1090x680.width} x {cover_1090x680.height}")
            return

        x1 = 514
        x2 = 578
        front_file_name = f"{file_title}.front.png"
        front_file_path = os.path.join(
            self.adjust_covers_folder_path(), front_file_name)
        if os.path.exists(front_file_path):
            cover_1090x680.paste(Image.open(front_file_path).resize(
                (cover_1090x680.width - x2, cover_1090x680.height)), (x2, 0))
            self.file_names_adjusted.append(front_file_name)
        else:
            print(f"封面文件缺失：{front_file_name}")

        back_file_name = f"{file_title}.back.png"
        back_filer_path = os.path.join(
            self.adjust_covers_folder_path(), back_file_name)
        if os.path.exists(back_filer_path):
            cover_1090x680.paste(Image.open(back_filer_path).resize(
                (x1, cover_1090x680.height)), (0, 0))
            self.file_names_adjusted.append(back_file_name)
        else:
            print(f"封底文件缺失：{back_file_name}")

        self.save_wiiflow_boxcover(file_title, cover_1090x680)

    def adjust_cover_1144x690(self, file_title, cover_1144x690):
        cover_1090x680 = Image.open(self.standard_cover_path())
        if cover_1090x680.width != 1090 or cover_1090x680.height != 680:
            print(
                f"standard_cover error: {cover_1090x680.width} x {cover_1090x680.height}")
            return

        x1_1090x680 = 514
        x2_1090x680 = 578

        x1_1144x690 = 506
        x2_1144x690 = 638

        back_box = [0, 0, x1_1144x690, cover_1144x690.height]
        back_crop = cover_1144x690.crop(back_box).resize(
            (x1_1090x680, cover_1090x680.height))
        cover_1090x680.paste(back_crop, (0, 0))

        mid_box = [x1_1144x690, 0, x2_1144x690, cover_1144x690.height]
        mid_crop = cover_1144x690.crop(mid_box).resize(
            (x2_1090x680 - x1_1090x680, cover_1090x680.height))
        cover_1090x680.paste(mid_crop, (x1_1090x680, 0))

        front_box = [x2_1144x690, 0,
                     cover_1144x690.width, cover_1144x690.height]
        front_crop = cover_1144x690.crop(front_box).resize(
            (cover_1090x680.width - x2_1090x680, cover_1090x680.height))
        cover_1090x680.paste(front_crop, (x2_1090x680, 0))

        self.save_wiiflow_boxcover(file_title, cover_1090x680)

    def adjust_cover_1090x680(self, file_title, cover_1090x680):
        x1_src = 482
        x2_src = 608

        x1_dst = 514
        x2_dst = 578

        back_box = [0, 0, x1_src, cover_1090x680.height]
        back_crop = cover_1090x680.crop(back_box).resize(
            (x1_dst, cover_1090x680.height))

        mid_box = [x1_src, 0, x2_src, cover_1090x680.height]
        mid_crop = cover_1090x680.crop(mid_box).resize(
            (x2_dst - x1_dst, cover_1090x680.height))

        front_box = [x2_src, 0, cover_1090x680.width, cover_1090x680.height]
        front_crop = cover_1090x680.crop(front_box).resize(
            (cover_1090x680.width - x2_dst, cover_1090x680.height))

        cover_1090x680.paste(back_crop, (0, 0))
        cover_1090x680.paste(mid_crop, (x1_dst, 0))
        cover_1090x680.paste(front_crop, (x2_dst, 0))

        self.save_wiiflow_boxcover(file_title, cover_1090x680)

    def run(self):
        if not folder_exist(self.adjust_covers_folder_path()):
            return

        for file_name in os.listdir(self.adjust_covers_folder_path()):
            if not file_name.endswith(".png") or file_name in self.file_names_adjusted:
                continue

            file_title = file_name.split(".")[0]
            if file_name.endswith(".front.png") or file_name.endswith(".back.png"):
                self.combine_front_and_back_cover(file_title)
            else:
                file_path = os.path.join(
                    self.adjust_covers_folder_path(), file_name)
                image = Image.open(file_path)
                if image.width == 1144 and image.height == 690:
                    self.adjust_cover_1144x690(file_title, image)
                    self.file_names_adjusted.append(file_name)
                elif image.width == 1090 and image.height == 680:
                    self.adjust_cover_1090x680(file_title, image)
                    self.file_names_adjusted.append(file_name)
                else:
                    print(f"{file_name} error: {image.width} x {image.height}")
