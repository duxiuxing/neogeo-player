# -- coding: UTF-8 --

from console_base import ConsoleBase


class CmdHandler:
    def __init__(self, tips):
        self.tips = tips

    def run(self):
        raise NotImplementedError()


class Quit(CmdHandler):
    def __init__(self):
        super().__init__("退出程序")

    def run(self):
        exit()


class ImportNewRoms(CmdHandler):
    def __init__(self):
        super().__init__("从 new_roms 文件夹导入新的游戏文件（.zip 格式）")

    def run(self):
        MainMenu.console.import_new_roms()


class CheckExistGamesInfos(CmdHandler):
    def __init__(self):
        super().__init__("检查 roms\\all.xml 中的游戏信息")

    def run(self):
        MainMenu.console.check_exist_games_infos()


class ConvertWfcFiles(CmdHandler):
    def __init__(self):
        super().__init__("把 wiiflow 文件夹里的图片转换成 cache 文件（.wfc 格式）")

    def run(self):
        MainMenu.console.wiiflow.convert_wfc_files()


class ConvertGameSynopsis(CmdHandler):
    def __init__(self):
        super().__init__("把 game_synopsis.md 里的游戏摘要文本转换成 WiiFlow 需要的排版格式")

    def run(self):
        MainMenu.console.wiiflow.convert_game_synopsis()


class ExportPluginToWiiSdCard(CmdHandler):
    def __init__(self):
        super().__init__("导出 WiiFlow 的插件文件到 Wii 的 SD 卡")

    def run(self):
        MainMenu.console.wiiflow.export_plugin()
        MainMenu.console.wiiflow.export_plugins_data()
        MainMenu.console.wiiflow.export_source_menu()


class ExportFakeGamesToWiiSdCard(CmdHandler):
    def __init__(self):
        super().__init__("导出【空白的】游戏文件（ROM.zip、封面.wfc 和 截图.png）到 Wii 的 SD 卡")

    def run(self):
        MainMenu.console.wiiflow.export_fake_roms()
        MainMenu.console.wiiflow.export_cache()
        MainMenu.console.wiiflow.export_snapshots()


class ExportGamesToWiiSdCard(CmdHandler):
    def __init__(self):
        super().__init__("导出【正常的】游戏文件（ROM.zip、封面.wfc 和 截图.png）到 Wii 的 SD 卡")

    def run(self):
        MainMenu.console.wiiflow.export_roms()
        MainMenu.console.wiiflow.export_cache()
        MainMenu.console.wiiflow.export_snapshots()


class ExportPngCoversToWiiSdCard(CmdHandler):
    def __init__(self):
        super().__init__("导出游戏封面的原图到 Wii 的 SD 卡")

    def run(self):
        MainMenu.console.wiiflow.export_png_boxcovers()


class MainMenu:
    console = None
    cmd_handler_list = {}

    @staticmethod
    def add_cmd_handler(cmd_handler):
        key = len(MainMenu.cmd_handler_list) + 1
        MainMenu.cmd_handler_list[str(key)] = cmd_handler

    @staticmethod
    def init_default_cmd_handlers():
        MainMenu.add_cmd_handler(ImportNewRoms())
        MainMenu.add_cmd_handler(CheckExistGamesInfos())
        MainMenu.add_cmd_handler(ConvertWfcFiles())
        MainMenu.add_cmd_handler(ConvertGameSynopsis())
        MainMenu.add_cmd_handler(ExportPluginToWiiSdCard())
        MainMenu.add_cmd_handler(ExportFakeGamesToWiiSdCard())
        MainMenu.add_cmd_handler(ExportGamesToWiiSdCard())
        MainMenu.add_cmd_handler(ExportPngCoversToWiiSdCard())

    @staticmethod
    def show():
        MainMenu.add_cmd_handler(Quit())

        while True:
            print("\n\n")
            if MainMenu.console is not None:
                print(f"机种代码：{MainMenu.console.wiiflow.plugin_name}")
            print("主菜单：")
            for key in range(1, len(MainMenu.cmd_handler_list) + 1):
                print(f"\t{key}. {MainMenu.cmd_handler_list[str(key)].tips}")

            input_value = str(input("\n请输入数字序号，选择要执行的操作："))
            if input_value in MainMenu.cmd_handler_list.keys():
                MainMenu.cmd_handler_list[input_value].run()
                print("\n操作完毕")
