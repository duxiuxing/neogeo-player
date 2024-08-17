# -- coding: UTF-8 --

import os

from console_impl import ConsoleImpl
from export_wii_apps import ExportWiiApps
from local_configs import LocalConfigs
from main_menu import MainMenu
from wiiflow import WiiFlow


class NeoGeoPocket(ConsoleImpl):
    def create_wiiflow(self):
        return WiiFlow(self, "NEOPOCKET")

    def root_folder_path(self):
        return os.path.join(LocalConfigs.repository_folder_path(), "pocket")


wii_app_files_tuple = (
    "apps\\ra-neogeo\\boot.dol",
    "apps\\ra-neogeo\\icon.png",
    "apps\\ra-neogeo\\meta.xml",
    "private"
)


MainMenu.console = NeoGeoPocket()
MainMenu.init_default_cmd_handlers()
# MainMenu.add_cmd_handler(ExportWiiApps(wii_app_files_tuple))
# MainMenu.add_cmd_handler(AdjustCovers())
MainMenu.show()
