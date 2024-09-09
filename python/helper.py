# -- coding: UTF-8 --

import os
import shutil
import zlib


class Helper:
    @staticmethod
    def compute_crc32(file_path):
        # 计算指定文件的 CRC32 值
        # Args:
        #     file_path (str): 文件路径，通常是游戏的 ROM 文件
        # Returns:
        #     str: 文件的 CRC32 值，八位大写十六进制字符串
        with open(file_path, 'rb') as file:
            data = file.read()
            crc = zlib.crc32(data)
            crc32 = hex(crc & 0xFFFFFFFF)[2:].upper()
            return crc32.rjust(8, "0")

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def verify_folder_exist_ex(folder_full_path):
        # 判断指定文件夹是否存在，如果不存在则逐级创建
        # Args:
        #     folder_path (str): 待判断的文件夹路径，如果父文件夹不存在会逐级创建
        # Returns:
        #     bool: 如果文件夹存在或创建成功，则返回 True，否则返回 False
        folder_path = ""
        for folder_name in folder_full_path.split("\\"):
            if folder_path == "":
                folder_path = folder_name
                if not os.path.isdir(folder_path):
                    return False
            else:
                if not os.path.isdir(folder_path):
                    return False
                folder_path = f"{folder_path}\\{folder_name}"
                if not os.path.isdir(folder_path):
                    os.mkdir(folder_path)
        return os.path.isdir(folder_full_path)

    @staticmethod
    def copy_folder(src, dst):
        # 用递归的方式，复制文件夹
        # Args:
        #     src (str): 源文件夹路径
        #     dst (str): 目标文件夹路径
        if not Helper.verify_folder_exist_ex(dst):
            return
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                Helper.copy_folder(s, d)
            elif not os.path.exists(d):
                shutil.copy2(s, d)

    @staticmethod
    def copy_file(src, dst):
        # 复制文件
        # Args:
        #     src (str): 源文件路径
        #     dst (str): 目标文件路径，如果父文件夹不存在会逐级创建
        if not Helper.verify_folder_exist_ex(os.path.dirname(dst)):
            return
        if not os.path.exists(dst):
            if os.path.exists(src):
                shutil.copy2(src, dst)
            else:
                print(f"源文件缺失：{src}")

    @staticmethod
    def copy_file_if_not_exist(src_file_path, dst_file_path):
        # 复制源文件到目标路径，如果目标文件已存在则跳过
        # Args:
        #     src_file_path (str): 源文件路径
        #     dst_file_path (str): 目标文件路径
        if not os.path.exists(src_file_path):
            print(f"源文件缺失：{src_file_path}")
        elif not os.path.exists(dst_file_path):
            shutil.copyfile(src_file_path, dst_file_path)
