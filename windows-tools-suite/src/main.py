import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from .ui.md5_calculator_ui import MD5CalculatorUI
from .ui.file_generator_ui import FileGeneratorUI
from .utils.logger import Logger

class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        self.logger = Logger("MainWindow")
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 添加MD5计算器标签页
        self.md5_calculator = MD5CalculatorUI()
        self.tab_widget.addTab(self.md5_calculator, 'MD5计算器')
        
        # 添加文件生成器标签页
        self.file_generator = FileGeneratorUI()
        self.tab_widget.addTab(self.file_generator, '文件生成器')
        
        # 设置中心窗口部件
        self.setCentralWidget(self.tab_widget)
        
        # 设置窗口标题和大小
        self.setWindowTitle('Windows工具套件')
        self.resize(800, 600)

def main():
    """主程序入口"""
    try:
        # 创建应用程序
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        # 运行应用程序
        sys.exit(app.exec_())
        
    except Exception as e:
        logger = Logger("Main")
        logger.error(f"程序运行出错: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()