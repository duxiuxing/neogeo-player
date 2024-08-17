# -- coding: UTF-8 --

class Console:
    def root_folder_path(self):
        # 仓库的第一级文件夹对应了不同的机种，以 cps-player 仓库为例：
        # - cps-player\\cps1 文件夹对应卡普空街机1代
        # - cps-player\\cps2 文件夹对应卡普空街机2代
        # - cps-player\\cps3 文件夹对应卡普空街机3代
        # 具体的文件夹路径需要由不同机种对应的类各自实现
        raise NotImplementedError()

    def wiiflow(self):
        # WiiFow 类型的实例，在派生类的构造函数中创建
        raise NotImplementedError()
    
    def import_new_roms(self):
        # 导入 new_roms 文件夹里的游戏文件（.zip 格式）
        raise NotImplementedError()
    
    def check_exist_games_infos(self):
        # 检查 roms\\all.xml 中的游戏信息
        raise NotImplementedError()