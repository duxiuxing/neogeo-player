# -- coding: UTF-8 --

class ConsoleConfigs:
    # 仓库的第一级文件夹对应了不同的机种，以 cps-player 仓库为例：
    # - cps-player\\cps1 文件夹对应卡普空街机1代
    # - cps-player\\cps2 文件夹对应卡普空街机2代
    # - cps-player\\cps3 文件夹对应卡普空街机3代
    # 具体的文件夹路径需要由不同机种对应的类各自实现
    def root_folder_path(self):
        raise NotImplementedError()
