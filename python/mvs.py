# -- coding: UTF-8 --

import os

from console_base import ConsoleBase
from export_wii_apps import ExportWiiApps
from local_configs import LocalConfigs
from main_menu import MainMenu
from mvs_adjust_covers import AdjustCovers
from wiiflow import WiiFlow


class NeoGeoMVS(ConsoleBase):
    def __init__(self, version_number):
        super().__init__()
        self.wiiflow = WiiFlow(self, "NEOGEO")

    def root_folder_path(self):
        return os.path.join(LocalConfigs.REPOSITORY_FOLDER, "mvs")


wii_app_files_tuple = (
    "apps\\ra-neogeo\\boot.dol",
    "apps\\ra-neogeo\\icon.png",
    "apps\\ra-neogeo\\meta.xml",
    "private"
)


MainMenu.console = NeoGeoMVS(1)
MainMenu.init_default_cmd_handlers()
MainMenu.add_cmd_handler(ExportWiiApps(wii_app_files_tuple))
MainMenu.add_cmd_handler(AdjustCovers())
MainMenu.show()
