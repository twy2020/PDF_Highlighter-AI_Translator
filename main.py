import sys
import traceback
import os  # 导入os模块
from PyQt5 import QtWidgets, QtGui, QtCore
from gui.main_window import PDFHighlighter

def excepthook(exctype, value, tb):
    """全局异常处理"""
    traceback.print_exception(exctype, value, tb)
    QtWidgets.QMessageBox.critical(
        None, 
        "未处理错误", 
        f"错误类型: {exctype.__name__}\n错误信息: {str(value)}"
    )

def main():
    # 设置基础路径 - 这里使用用户文档目录
    base_path = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.DocumentsLocation
    )
    
    # 如果命令行没有提供文件路径
    if len(sys.argv) < 2:
        app = QtWidgets.QApplication(sys.argv)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, 
            "打开PDF文件", 
            base_path,  # 使用基础路径作为默认目录
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return
    else:
        file_path = sys.argv[1]
    
    sys.excepthook = excepthook
    
    # 如果已经创建了QApplication实例则复用
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    
    # 设置默认字体
    font = QtGui.QFont()
    font.setFamily("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)
    
    viewer = PDFHighlighter(file_path)
    viewer.resize(1200, 900)
    viewer.show()
    
    # 确保暗黑模式状态同步
    if hasattr(viewer, 'dark_mode_action'):
        viewer.dark_mode_action.setChecked(viewer.is_dark_mode)
    
    # 确保对比度滑块位置正确
    if hasattr(viewer, 'contrast_slider'):
        viewer.contrast_slider.setValue(int(viewer.contrast_level * 100))
        # 连接对比度滑块信号
        viewer.contrast_slider.valueChanged.connect(viewer.set_contrast_level)
        
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()