import fitz
import uuid
import time
import os
import json
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from .graphics_view import GraphicsView
from .highlight_manager import HighlightManager
from .table_manager import TableManager
from .export_manager import ExportManager
from translator import translate_sentences, extract_and_translate_words
from utils import clean_text
import threading
from .thread_manager import TranslationWorker
from .api_set import ApiSetPanel, PromptSetPanel

class PDFHighlighter(QtWidgets.QMainWindow):
    def __init__(self, pdf_path):
        super().__init__()
        # 1. 初始化文档相关属性
        self.doc = fitz.open(pdf_path)
        self.page_index = 0
        self.zoom = 1.5
        self.thumbnail_size = (120, 160)
        self.thumb_dock = None
        self.contrast_level = 0.7
        self.thumbnails = []  # 确保缩略图列表在类创建时就存在
        self.thumbnail_labels = []

        # 添加工具栏布局控制变量
        self.toolbar_layout_spacing = 4  # 固定间距值
        self.toolbar_layout_margins = (2, 2, 2, 2)  # 固定边距值
        
        # 2. 初始化选择信息
        self.selection_info = {
            "text": "", 
            "page_index": None,
            "timestamp": None
        }
        
        # 3. 初始化模式相关属性
        self.is_dark_mode = False
        self.invert_pdf_colors = False
        
        # 4. 初始化核心组件
        self.view = GraphicsView(self)
        self.highlight_manager = HighlightManager(self.doc, self.view)
        self.table_manager = TableManager(self.highlight_manager)
        
        # 5. 创建箭头图标
        self.create_arrow_icons()
        
        # 6. 初始化UI
        self.setup_ui()

        # 7. 初始化其他属性
        self.SELECTION_TIMEOUT = 300  # 5分钟
        self.active_workers = {}  # 存储当前活动的工作线程
        self.current_page_lock = threading.Lock()  # 页面索引锁
        
        # 8. 设置暗黑模式 - 现在所有UI组件都已创建
        self.setup_dark_mode()  # 初始化模式

        # 确保按钮状态正确同步
        self.sync_ui_states()  # 新增方法调用

        if hasattr(self, 'invert_action'):
            self.invert_action.setChecked(self.invert_pdf_colors)

        if hasattr(self, 'dark_mode_action'):
            if self.is_dark_mode:
                self.dark_mode_action.setText("切换白天")
            else:
                self.dark_mode_action.setText("切换暗黑")
        
        # 确保API设置面板加载了配置
        if hasattr(self, 'api_set_panel'):
            self.api_set_panel.load_config()
        
        self.load_page()
        
        # 初始化左侧dock宽度
        self.saved_left_dock_width = self.left_dock.width()
        
        # 连接信号
        self.setup_connections()
        
        # 确保布局完全应用
        QtCore.QTimer.singleShot(100, self.finalize_layout)
        
        self.setWindowTitle(f"PDF Highlighter ({self.doc.page_count} pages)")
        self.resize(1500, 900)  # 增加窗口宽度以适应新dock

    def setup_ui(self):
        # 创建工具栏
        self.setup_toolbar()
        
        # 设置中心视图
        self.setCentralWidget(self.view)
        
        # 创建左侧面板
        self.setup_left_panel()
        
        # 创建缩略图预览dock
        if not self.thumb_dock:
            self.setup_thumbnail_dock()
        
        # 创建右侧面板
        self.setup_right_panel()

        self.setup_word_buttons()
        self.setup_sentence_buttons()
        
        # 创建导航栏
        self.setup_navigation()
        
        # 调整dock布局：将缩略图dock放在左侧dock的右侧
        self.splitDockWidget(self.left_dock, self.thumb_dock, QtCore.Qt.Horizontal)
        
        # 设置dock大小比例
        self.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks)
        
        # 固定左侧dock的宽度
        self.left_dock.setFixedWidth(300)
        
        # 确保布局完全应用
        QtCore.QTimer.singleShot(100, self.finalize_layout)
        
        self.setWindowTitle(f"PDF Highlighter ({self.doc.page_count} pages)")
        self.resize(1500, 900)  # 增加窗口宽度以适应新dock

    def setup_toolbar(self):
        """设置工具栏 - 使用默认样式，缩小按钮"""
        self.toolbar = self.addToolBar("文件")
        self.toolbar.setIconSize(QtCore.QSize(16, 16))  # 缩小图标尺寸
        
        # 打开PDF按钮
        open_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("document-open"), "打开PDF", self)
        open_action.triggered.connect(self.open_pdf)
        self.toolbar.addAction(open_action)
        
        # 导出带高亮PDF按钮
        export_pdf_action = QtWidgets.QAction("导出PDF", self)  # 缩短文本
        export_pdf_action.triggered.connect(self.export_highlighted_pdf)
        self.toolbar.addAction(export_pdf_action)
        
        # 添加分隔线
        self.toolbar.addSeparator()
        
        # 缩放按钮
        zoom_in_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("zoom-in"), "放大", self)
        zoom_in_action.triggered.connect(lambda: self.adjust_zoom(1.25))
        self.toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QtWidgets.QAction(QtGui.QIcon.fromTheme("zoom-out"), "缩小", self)
        zoom_out_action.triggered.connect(lambda: self.adjust_zoom(0.8))
        self.toolbar.addAction(zoom_out_action)
        
        # 添加分隔线
        self.toolbar.addSeparator()
        
        # 暗黑模式按钮
        self.dark_mode_action = QtWidgets.QAction("暗黑", self)  # 缩短文本
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(self.is_dark_mode)
        self.dark_mode_action.toggled.connect(self.toggle_dark_mode)
        self.toolbar.addAction(self.dark_mode_action)
        
        # PDF颜色翻转按钮
        self.invert_action = QtWidgets.QAction("翻转", self)  # 缩短文本
        self.invert_action.setCheckable(True)
        self.invert_action.setChecked(self.invert_pdf_colors)
        self.invert_action.toggled.connect(self.toggle_invert_colors)
        self.toolbar.addAction(self.invert_action)
        
        # 添加分隔线
        self.toolbar.addSeparator()
        
        # 对比度控件
        contrast_label = QtWidgets.QLabel("对比度:")
        contrast_label.setFixedWidth(60)  # 缩小标签宽度
        self.toolbar.addWidget(contrast_label)
        
        self.contrast_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.contrast_slider.setRange(20, 100)
        self.contrast_slider.setValue(int(self.contrast_level * 100))
        self.contrast_slider.setFixedWidth(80)  # 缩小滑块宽度
        
        # 连接对比度滑块信号
        self.contrast_slider.valueChanged.connect(self.set_contrast_level)
        
        self.toolbar.addWidget(self.contrast_slider)
        
        # 帮助按钮
        help_menu = QtWidgets.QMenu("帮助", self)

        usage_action = QtWidgets.QAction("使用说明", self)
        usage_action.triggered.connect(self.open_usage_guide)
        help_menu.addAction(usage_action)

        # 关于项
        about_action = QtWidgets.QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        help_button = QtWidgets.QToolButton()
        help_button.setMenu(help_menu)
        help_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        help_button.setText("帮助")
        help_button.setFixedWidth(40)  # 缩小按钮宽度
        self.toolbar.addWidget(help_button)

    def open_pdf(self):
        """打开新的PDF文件"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "打开PDF文件", "", "PDF Files (*.pdf)"
        )
        if file_path:
            try:
                # 1. 关闭现有文档
                if hasattr(self, 'doc') and self.doc:
                    self.doc.close()
                
                # 2. 重置预览相关状态
                self.thumbnails = []  # 重置缩略图列表
                self.thumbnail_labels = []  # 重置缩略图标签列表
                
                # 3. 移除现有的预览dock
                if hasattr(self, 'thumb_dock') and self.thumb_dock:
                    self.thumb_dock.close()
                    self.thumb_dock.deleteLater()
                    self.thumb_dock = None
                
                # 4. 打开新文档
                self.doc = fitz.open(file_path)
                self.page_index = 0
                self.highlight_manager = HighlightManager(self.doc, self.view)
                
                # 5. 重新加载页面和预览
                self.load_page()
                self.setWindowTitle(f"PDF Highlighter ({self.doc.page_count} pages)")
                self.log(f"已打开文件: {file_path}")
                
                # 6. 重新创建缩略图预览dock
                self.setup_thumbnail_dock()
                self.splitDockWidget(self.left_dock, self.thumb_dock, QtCore.Qt.Horizontal)
                
                # 7. 更新缩略图预览
                self.update_thumbnail_previews()
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")

    def adjust_zoom(self, factor):
        """调整缩放比例"""
        self.zoom *= factor
        self.load_page()
        self.log(f"缩放比例: {self.zoom:.2f}")

    def show_about(self):
        """显示关于对话框"""
        about_text = (
            "<h2>PDF Highlighter</h2>"
            "<p><b>版本 1.0.0</b></p>"
            "<p>一个基于大语言模型的PDF文档标注和翻译工具</p>"
            "<p>主要功能：</p>"
            "<ul>"
            "<li>选择文本并翻译整段内容</li>"
            "<li>提取并翻译生词</li>"
            "<li>高亮重要内容并添加注释</li>"
            "<li>导出带注释的PDF文件</li>"
            "<li>导出单词和句子翻译</li>"
            "</ul>"
            "<p>技术支持：tenwonyun@gmail.com</p>"
        )
        
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("关于 PDF Highlighter")
        msg_box.setTextFormat(QtCore.Qt.RichText)
        msg_box.setText(about_text)
        msg_box.setIconPixmap(QtGui.QPixmap(":/icons/app_icon.png").scaled(64, 64))  # 如果有应用图标
        msg_box.exec_()

    def open_usage_guide(self):
        """打开使用说明链接"""
        usage_url = "https://github.com/twy2020/PDF_Highlighter-AI_Translator#"  # 替换为您的实际链接
        
        # 使用QDesktopServices打开链接
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(usage_url))
        
        # 记录日志
        self.log(f"已打开使用说明: {usage_url}")

    def setup_left_panel(self):
        """设置左侧面板（API设置、Prompt设置和文本选择区域）"""
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        
        # 添加API设置面板
        self.api_set_panel = ApiSetPanel(self)
        left_layout.addWidget(self.api_set_panel)
        
        # 添加分隔线
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        left_layout.addWidget(line)
        
        # 添加Prompt设置面板（只包含单词提取条件设置）
        self.prompt_set_panel = PromptSetPanel(self)
        left_layout.addWidget(self.prompt_set_panel)
        
        # 添加分隔线
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        left_layout.addWidget(line)
        
        # 添加文本选择区域标题
        text_select_label = QtWidgets.QLabel("文本选择")
        text_select_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(text_select_label)
        
        # 添加选择来源页面标签
        self.selection_page_label = QtWidgets.QLabel("当前无选择")
        self.selection_page_label.setStyleSheet("font-style: italic;")
        left_layout.addWidget(self.selection_page_label)
        
        self.selection_box = QtWidgets.QTextEdit(readOnly=True)
        self.selection_box.setObjectName("selection_box")  # 设置对象名以便样式表应用
        left_layout.addWidget(self.selection_box, 1)  # 文本框占据更多空间
        
        # 翻译按钮
        btn_translate_sentences = QtWidgets.QPushButton("翻译整段文本")
        btn_translate_sentences.setFixedHeight(40)
        btn_translate_sentences.setObjectName("btn_translate_sentences")  # 设置对象名
        
        # 提取单词按钮
        btn_extract_words = QtWidgets.QPushButton("提取并翻译生词")
        btn_extract_words.setFixedHeight(40)
        btn_extract_words.setObjectName("btn_extract_words")  # 设置对象名
        
        left_layout.addWidget(btn_translate_sentences)
        left_layout.addWidget(btn_extract_words)
        
        # 创建dock并禁止关闭
        dock_left = QtWidgets.QDockWidget("API设置与文本选择", self)
        dock_left.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        dock_left.setWidget(left)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_left)
        
        # 保存引用
        self.left_dock = dock_left
        
        # 设置左侧dock的固定宽度
        self.left_dock.setFixedWidth(300)

        # 连接按钮信号
        btn_translate_sentences.clicked.connect(self.translate_sentences)
        btn_extract_words.clicked.connect(self.extract_and_translate_words)

    def setup_right_panel(self):
        """设置右侧面板（翻译结果区域）"""
        # 主Widget
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        
        # 使用标签页组织内容
        self.tab_widget = QtWidgets.QTabWidget()
        
        # 单词翻译标签页
        word_tab = QtWidgets.QWidget()
        word_tab_l = QtWidgets.QVBoxLayout(word_tab)

        # 添加单词按钮容器
        word_tab_l.addWidget(self.table_manager.word_button_container)
        
        # 单词操作按钮
        word_btn_frame = QtWidgets.QFrame()
        word_btn_layout = QtWidgets.QHBoxLayout(word_btn_frame)
        for text, handler in [
            ("全选单词", self.select_all_words),
            ("高亮选中", self.highlight_selected_words),
            ("清除选中", self.unhighlight_selected_words),
            ("删除选中", self.delete_selected_words),
        ]:
            btn = QtWidgets.QPushButton(text)
            btn.clicked.connect(handler)
            word_btn_layout.addWidget(btn)
        
        # 单词导出按钮
        export_btn_frame = QtWidgets.QFrame()
        export_btn_layout = QtWidgets.QHBoxLayout(export_btn_frame)
        btn_export_page = QtWidgets.QPushButton("导出此页单词")
        btn_export_page.clicked.connect(self.export_current_page_words)
        btn_export_all = QtWidgets.QPushButton("导出全部单词")
        btn_export_all.clicked.connect(self.export_all_pages_words)
        export_btn_layout.addWidget(btn_export_page)
        export_btn_layout.addWidget(btn_export_all)
        
        # 单词表格
        self.table_manager.word_table.cellClicked.connect(self.toggle_word_highlight)
        word_tab_l.addWidget(word_btn_frame)
        word_tab_l.addWidget(export_btn_frame)
        word_tab_l.addWidget(self.table_manager.word_table)
        
        # 句子翻译标签页
        sentence_tab = QtWidgets.QWidget()
        sentence_tab_l = QtWidgets.QVBoxLayout(sentence_tab)

        # 添加句子按钮容器
        sentence_tab_l.addWidget(self.table_manager.sentence_button_container)
        
        # 句子操作按钮
        sentence_btn_frame = QtWidgets.QFrame()
        sentence_btn_layout = QtWidgets.QHBoxLayout(sentence_btn_frame)
        btn_highlight_sentence = QtWidgets.QPushButton("高亮选中句子")
        btn_highlight_sentence.clicked.connect(self.highlight_selected_sentences)
        btn_clear_sentence = QtWidgets.QPushButton("清除选中句子")
        btn_clear_sentence.clicked.connect(self.unhighlight_selected_sentences)
        btn_delete_sentence = QtWidgets.QPushButton("删除选中句子")
        btn_delete_sentence.clicked.connect(self.delete_selected_sentences)
        sentence_btn_layout.addWidget(btn_highlight_sentence)
        sentence_btn_layout.addWidget(btn_clear_sentence)
        sentence_btn_layout.addWidget(btn_delete_sentence)
        
        # 句子导出按钮
        sentence_export_frame = QtWidgets.QFrame()
        sentence_export_layout = QtWidgets.QHBoxLayout(sentence_export_frame)
        btn_export_page_sentences = QtWidgets.QPushButton("导出本页句子")
        btn_export_page_sentences.clicked.connect(self.export_current_page_sentences)
        btn_export_all_sentences = QtWidgets.QPushButton("导出全部句子")
        btn_export_all_sentences.clicked.connect(self.export_all_sentences)
        sentence_export_layout.addWidget(btn_export_page_sentences)
        sentence_export_layout.addWidget(btn_export_all_sentences)
        
        # 句子表格
        self.table_manager.sentence_table.cellClicked.connect(self.toggle_sentence_highlight)
        sentence_tab_l.addWidget(sentence_btn_frame)
        sentence_tab_l.addWidget(sentence_export_frame)
        sentence_tab_l.addWidget(self.table_manager.sentence_table)
        
        # 添加标签页
        self.tab_widget.addTab(word_tab, "单词翻译")
        self.tab_widget.addTab(sentence_tab, "句子翻译")
        
        # 添加标签页到主布局
        right_layout.addWidget(self.tab_widget, 1)  # 标签页占据主要空间
        
        # 添加分隔线
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        right_layout.addWidget(separator)
        
        # 添加日志区域
        log_label = QtWidgets.QLabel("系统提示")
        log_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(log_label)
        
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("log_text")  # 设置对象名
        self.log_text.setMaximumHeight(100)  # 设置较小高度
        right_layout.addWidget(self.log_text)
        
        # 创建dock并禁止关闭
        dock_right = QtWidgets.QDockWidget("翻译结果", self)
        dock_right.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)  # 禁止关闭
        dock_right.setWidget(right_widget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_right)

    def setup_navigation(self):
        """设置导航栏（页面切换）"""
        nav_w = QtWidgets.QWidget()
        nav_l = QtWidgets.QHBoxLayout(nav_w)
        nav_l.setAlignment(QtCore.Qt.AlignCenter)  # 确保整体居中
        
        # 创建紧凑的控件容器
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)  # 减少边距
        container_layout.setSpacing(5)  # 紧凑间距
        
        # 上一页按钮
        btn_prev = QtWidgets.QPushButton("上一页")
        btn_prev.setFixedSize(70, 30)  # 稍微减小宽度
        btn_prev.clicked.connect(self.prev_page)
        
        # 页码标签
        self.page_label = QtWidgets.QLabel()
        self.page_label.setFixedSize(100, 30)  # 减小宽度
        self.page_label.setAlignment(QtCore.Qt.AlignCenter)
        self.page_label.setObjectName("page_label")
        
        # 跳转控件容器 - 更加紧凑
        jump_container = QtWidgets.QWidget()
        jump_layout = QtWidgets.QHBoxLayout(jump_container)
        jump_layout.setContentsMargins(0, 0, 0, 0)
        jump_layout.setSpacing(2)  # 最小间距
        
        # 跳转标签
        jump_label = QtWidgets.QLabel("跳至:")
        jump_layout.addWidget(jump_label)
        
        # 页码输入框
        self.page_jump_edit = QtWidgets.QLineEdit()
        self.page_jump_edit.setFixedWidth(35)  # 减小宽度
        self.page_jump_edit.setValidator(QtGui.QIntValidator(1, self.doc.page_count))
        self.page_jump_edit.setAlignment(QtCore.Qt.AlignCenter)
        self.page_jump_edit.returnPressed.connect(self.jump_to_page)
        jump_layout.addWidget(self.page_jump_edit)
        
        # 跳转按钮
        btn_jump = QtWidgets.QPushButton("GOTO")
        btn_jump.setFixedSize(60, 30)  # 减小宽度
        btn_jump.clicked.connect(self.jump_to_page)
        jump_layout.addWidget(btn_jump)
        
        # 下一页按钮
        btn_next = QtWidgets.QPushButton("下一页")
        btn_next.setFixedSize(70, 30)  # 稍微减小宽度
        btn_next.clicked.connect(self.next_page)
        
        # 将控件添加到布局
        container_layout.addWidget(btn_prev)
        container_layout.addWidget(self.page_label)
        container_layout.addWidget(jump_container)  # 添加紧凑的跳转控件组
        container_layout.addWidget(btn_next)
        
        # 添加左右弹性空间使容器居中
        nav_l.addStretch(1)
        nav_l.addWidget(container)
        nav_l.addStretch(1)
        
        # 创建导航dock
        dock_nav = QtWidgets.QDockWidget("", self)
        dock_nav.setTitleBarWidget(QtWidgets.QWidget())  # 隐藏标题栏
        dock_nav.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)  # 禁止关闭
        dock_nav.setWidget(nav_w)
        dock_nav.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_nav)
        
        # 初始页码
        self.update_page_label()

    def jump_to_page(self):
        """跳转到指定页面"""
        try:
            # 获取输入框中的页码
            page_num = int(self.page_jump_edit.text())
            
            # 检查页码是否在有效范围内
            if 1 <= page_num <= self.doc.page_count:
                # 更新当前页面索引（索引从0开始）
                self.page_index = page_num - 1
                self.load_page()
            else:
                # 显示错误提示
                self.log(f"无效页码：请输入1-{self.doc.page_count}之间的数字")
        except ValueError:
            # 输入不是数字
            self.log("请输入有效的页码数字")
        
        # 清空输入框
        self.page_jump_edit.clear()
        
        # 焦点回到主视图
        self.view.setFocus()

    def update_page_label(self):
        """更新页码标签"""
        self.page_label.setText(f"{self.page_index + 1}/{self.doc.page_count}")
        
        # 更新跳转输入框的验证器范围
        if hasattr(self, 'page_jump_edit'):
            self.page_jump_edit.validator().setTop(self.doc.page_count)

    def setup_log_area(self):
        """设置日志区域"""
        log_widget = QtWidgets.QWidget()
        log_layout = QtWidgets.QVBoxLayout(log_widget)
        
        # 日志标签
        log_label = QtWidgets.QLabel("系统提示")
        log_label.setStyleSheet("font-weight: bold;")
        log_layout.addWidget(log_label)
        
        # 日志文本框 - 使用简单的文本编辑框
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background:#f5f5f5; font-family: monospace;")
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        dock_log = QtWidgets.QDockWidget("", self)
        dock_log.setWidget(log_widget)
        dock_log.setAllowedAreas(
            QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.RightDockWidgetArea
        )
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_log)

    def setup_connections(self):
        """设置信号连接"""
        # 单词表格操作
        self.table_manager.word_table.cellPressed.connect(self.toggle_word_highlight)
        
        # 句子表格操作
        self.table_manager.sentence_table.cellPressed.connect(self.toggle_sentence_highlight)

    def log(self, message: str):
        """在系统提示框里输出一行带时间戳的消息"""
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"[{ts}] {message}")
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def update_selection_display(self, text: str):
        """更新选中的文本显示"""
        # 记录选择时的页面和时间戳
        self.selection_info = {
            "text": text,
            "page_index": self.page_index,  # 确保使用当前页面索引
            "timestamp": time.time()
        }
        
        self.selection_box.setPlainText(text)
        self.update_selection_ui()  # 更新UI状态
        
        # 记录日志 - 使用用户友好页码（从1开始）
        page_num = self.page_index + 1 if self.page_index is not None else "未知"
        self.log(f"已选择文本，长度 {len(text)} 字符 (页面 {page_num})")

    def load_page(self):
        """加载当前页内容（增加颜色翻转和对比度调整功能）"""
        with self.current_page_lock:
            self.highlight_manager.set_zoom(self.zoom)
            
            page = self.doc[self.page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
            
            # 创建基础图像
            img = QtGui.QImage(
                pix.samples, 
                pix.width, 
                pix.height,
                pix.stride, 
                QtGui.QImage.Format_RGB888
            )
            
            # PDF颜色翻转功能
            if self.invert_pdf_colors:
                # 创建反转后的图像
                inverted_img = QtGui.QImage(img.size(), QtGui.QImage.Format_RGB888)
                inverted_img.fill(QtGui.QColor(255, 255, 255))  # 填充白色背景
                
                # 使用QPainter绘制反转后的图像
                painter = QtGui.QPainter(inverted_img)
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_Difference)
                painter.drawImage(0, 0, img)
                painter.end()
                
                img = inverted_img
                
                # 降低对比度效果 - 新增部分
                # 创建临时图像用于调整对比度
                contrast_img = QtGui.QImage(img.size(), QtGui.QImage.Format_RGB888)
                contrast_img.fill(QtGui.QColor(128, 128, 128))  # 填充中灰色背景
                
                # 应用降低对比度效果
                painter = QtGui.QPainter(contrast_img)
                painter.setOpacity(self.contrast_level)  # 使用可配置的对比度级别
                painter.drawImage(0, 0, img)
                painter.end()
                
                img = contrast_img
            
            pixmap = QtGui.QPixmap.fromImage(img)
            
            # 修改：传递页面对象和页面索引
            self.view.set_page(pixmap, page, self.page_index, self.zoom)
            
            # 绘制当前页的高亮
            self.highlight_manager.draw_page_highlights(self.page_index)
            
            # 更新表格内容
            self.update_tables()
        
        # 更新页面切换提示
        self.update_selection_ui()
        # 更新页码标签
        self.update_page_label()

        if self.highlight_manager.get_page_translation_status(self.page_index) == 2:
            self.highlight_manager.clear_page_status(self.page_index)
            self.update_thumbnail_previews()
        
        # 更新缩略图高亮
        self.update_thumbnail_highlight()
        
        # 记录页面切换
        self.log(f"已切换到页面 {self.page_index + 1}/{self.doc.page_count}")

    def update_tables(self):
        """更新单词和句子表格"""
        # 更新单词表格
        word_map, highlighted_words = self.highlight_manager.get_word_highlight_info(self.page_index)
        self.table_manager.populate_word_table(word_map, highlighted_words)
        
        # 更新句子表格
        sentences, highlighted_ids = self.highlight_manager.get_sentence_highlight_info(self.page_index)
        self.table_manager.populate_sentence_table(sentences, highlighted_ids)
        
        # 强制刷新表格样式 - 新增
        self.table_manager.word_table.style().polish(self.table_manager.word_table)
        self.table_manager.sentence_table.style().polish(self.table_manager.sentence_table)

    def prev_page(self):
        """导航到上一页"""
        if self.page_index > 0:
            self.page_index -= 1
            self.load_page()

    def next_page(self):
        """导航到下一页"""
        if self.page_index < self.doc.page_count - 1:
            self.page_index += 1
            self.load_page()

    def translate_sentences(self):
        """翻译整段文本 - 多线程版本"""
        # 检查选择信息是否有效
        if not self.selection_info:
            self.log("警告：没有可用的选择信息")
            return
            
        # 检查选择是否过期 - 修复时间戳处理
        timestamp = self.selection_info.get("timestamp")
        if timestamp is None:
            self.log("警告：选择信息缺少时间戳")
            return
            
        # 确保时间戳是数字类型
        if not isinstance(timestamp, (int, float)):
            self.log("警告：时间戳格式无效")
            return
            
        if (time.time() - timestamp) > self.SELECTION_TIMEOUT:
            self.log("警告：选择已过期，请重新选择文本")
            return
                
        # 获取保存的选择信息
        text = self.selection_info.get("text", "").strip()
        if not text:
            self.log("警告：尝试翻译时没有选中文本")
            return
        
        # 添加上下文信息以改善匹配
        context_text = self.get_selection_with_context()
        if context_text:
            text = context_text + " " + text
        
        # 获取保存的页面索引
        selection_page = self.selection_info.get("page_index")
        
        # 检查选择是否属于当前页面
        if selection_page is not None and selection_page != self.page_index:
            # 显示确认对话框 - 添加页面检查
            selection_page_num = selection_page + 1 if selection_page is not None else "未知"
            current_page_num = self.page_index + 1 if self.page_index is not None else "未知"
            
            reply = QtWidgets.QMessageBox.question(
                self, "确认翻译",
                f"您选择的文本来自页面 {selection_page_num}，但您当前在页面 {current_page_num}。\n"
                "您确定要将翻译结果添加到原始页面吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            
            if reply == QtWidgets.QMessageBox.No:
                self.log("翻译已取消")
                return
        
        # 使用保存的页面索引
        page_index = selection_page if selection_page is not None else self.page_index
        
        # 确保页面索引有效
        if page_index is None:
            self.log("错误：无法确定页面索引")
            return
            
        self.log(f"提交整段翻译请求 (页面 {page_index + 1})")
        
        # 创建工作线程 - 使用保存的页面索引
        worker = TranslationWorker("sentences", text, page_index)
        worker_thread = QtCore.QThread()
        worker.moveToThread(worker_thread)
        
        # 连接信号
        worker.finished.connect(self.handle_translate_sentences_result)
        worker.error.connect(self.handle_translation_error)
        worker.progress.connect(self.log)
        
        # 存储工作线程
        self.active_workers[id(worker)] = (worker, worker_thread)
        
        # 开始工作
        worker_thread.started.connect(worker.run)
        worker_thread.start()

        # 新增：设置页面翻译状态
        self.highlight_manager.start_translation_task(page_index)
        self.update_thumbnail_previews()  # 立即更新缩略图
        
        # 添加日志 - 不再使用超链接
        self.log(f"[翻译进行中] 页面 {page_index + 1} - 处理中...")

    def extract_and_translate_words(self):
        """提取并翻译生词 - 多线程版本"""
        # 检查选择信息是否有效
        if not self.selection_info:
            self.log("警告：没有可用的选择信息")
            return
            
        # 检查选择是否过期 - 修复时间戳处理
        timestamp = self.selection_info.get("timestamp")
        if timestamp is None:
            self.log("警告：选择信息缺少时间戳")
            return
            
        # 确保时间戳是数字类型
        if not isinstance(timestamp, (int, float)):
            self.log("警告：时间戳格式无效")
            return
            
        if (time.time() - timestamp) > self.SELECTION_TIMEOUT:
            self.log("警告：选择已过期，请重新选择文本")
            return
            
        # 获取保存的选择信息
        text = self.selection_info.get("text", "").strip()
        if not text:
            self.log("警告：尝试提取生词时没有选中文本")
            return
        
        # 获取保存的页面索引
        selection_page = self.selection_info.get("page_index")
        
        # 检查选择是否属于当前页面
        if selection_page is not None and selection_page != self.page_index:
            # 显示确认对话框 - 添加页面检查
            selection_page_num = selection_page + 1 if selection_page is not None else "未知"
            current_page_num = self.page_index + 1 if self.page_index is not None else "未知"
            
            reply = QtWidgets.QMessageBox.question(
                self, "确认提取",
                f"您选择的文本来自页面 {selection_page_num}，但您当前在页面 {current_page_num}。\n"
                "您确定要将提取结果添加到原始页面吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            
            if reply == QtWidgets.QMessageBox.No:
                self.log("提取已取消")
                return
        
        # 使用保存的页面索引
        page_index = selection_page if selection_page is not None else self.page_index
        
        # 确保页面索引有效
        if page_index is None:
            self.log("错误：无法确定页面索引")
            return
            
        self.log(f"提交生词提取请求 (页面 {page_index + 1})")
        
        # 创建工作线程 - 使用保存的页面索引
        worker = TranslationWorker("words", text, page_index)
        worker_thread = QtCore.QThread()
        worker.moveToThread(worker_thread)
        
        # 连接信号
        worker.finished.connect(self.handle_extract_words_result)
        worker.error.connect(self.handle_translation_error)
        worker.progress.connect(self.log)
        
        # 存储工作线程
        self.active_workers[id(worker)] = (worker, worker_thread)
        
        # 开始工作
        worker_thread.started.connect(worker.run)
        worker_thread.start()

        self.highlight_manager.start_translation_task(page_index)
        self.update_thumbnail_previews()  # 立即更新缩略图
        
        # 添加日志 - 不再使用超链接
        self.log(f"[提取进行中] 页面 {page_index + 1} - 处理中...")

    # 单词操作
    def select_all_words(self):
        """全选单词表格中的行"""
        self.table_manager.word_table.selectAll()

    def highlight_selected_words(self):
        """高亮选中的单词（强制高亮）"""
        selected = False
        # 获取当前颜色
        color = self.table_manager.word_color_edit.text()
        
        for idx in self.table_manager.word_table.selectionModel().selectedRows():
            row = idx.row()
            word = self.table_manager.word_table.item(row, 1).text()
            
            # 高亮单词 - 使用当前颜色
            if self.highlight_manager.highlight_word(word, self.page_index, color):
                selected = True
        
        if selected:
            self.update_tables()
            # 更新缩略图
            self.update_thumbnail_previews()

    def unhighlight_selected_words(self):
        """取消高亮选中的单词"""
        selected = False
        for idx in self.table_manager.word_table.selectionModel().selectedRows():
            row = idx.row()
            word = self.table_manager.word_table.item(row, 1).text()
            
            # 取消高亮单词
            if self.highlight_manager.unhighlight_word(word, self.page_index):
                selected = True
        
        if selected:
            self.update_tables()
            # 更新缩略图
            self.update_thumbnail_previews()

    def toggle_word_highlight(self, row, col):
        """切换单词高亮状态"""
        if col != 0:  # 只处理第一列（高亮状态列）的点击
            return
        
        word = self.table_manager.word_table.item(row, 1).text()
        
        # 获取当前颜色
        color = self.table_manager.word_color_edit.text()
        
        # 使用新的 is_word_highlighted 方法
        if self.highlight_manager.is_word_highlighted(word, self.page_index):
            self.highlight_manager.unhighlight_word(word, self.page_index)
        else:
            # 使用当前颜色设置
            self.highlight_manager.highlight_word(word, self.page_index, color)
        
        # 更新表格
        self.update_tables()
        # 更新缩略图
        self.update_thumbnail_previews()

    # 句子操作
    def highlight_selected_sentences(self):
        """高亮选中的句子（强制高亮）"""
        selected = False
        # 获取当前颜色
        color = self.table_manager.sentence_color_edit.text()
        
        for idx in self.table_manager.sentence_table.selectionModel().selectedRows():
            row = idx.row()
            sentences = self.highlight_manager.get_current_page_sentences(self.page_index)
            if row < len(sentences):
                sent = sentences[row]
                if 'id' in sent:
                    # 高亮句子 - 使用当前颜色
                    if self.highlight_manager.highlight_sentence(sent['id'], self.page_index, color):
                        selected = True
        
        if selected:
            self.update_tables()
            # 刷新预览 - 确保句子高亮显示在缩略图中
            self.update_thumbnail_previews()

    def unhighlight_selected_sentences(self):
        """取消高亮选中的句子"""
        selected = False
        for idx in self.table_manager.sentence_table.selectionModel().selectedRows():
            row = idx.row()
            sentences = self.highlight_manager.get_current_page_sentences(self.page_index)
            if row < len(sentences):
                sent = sentences[row]
                if 'id' in sent:
                    # 取消高亮句子
                    if self.highlight_manager.unhighlight_sentence(sent['id']):
                        selected = True
        
        if selected:
            self.update_tables()
            # 更新缩略图
            self.update_thumbnail_previews()

    def delete_selected_sentences(self):
        """删除选中的句子"""
        rows_to_delete = sorted(
            [idx.row() for idx in self.table_manager.sentence_table.selectionModel().selectedRows()],
            reverse=True
        )
        
        delete_count = 0
        for row in rows_to_delete:
            sentences = self.highlight_manager.get_current_page_sentences(self.page_index)
            if row < len(sentences):
                sent = sentences[row]
                if 'id' in sent:
                    # 移除句子 - 使用新添加的 remove_sentence 方法
                    self.highlight_manager.remove_sentence(sent['id'])
                    delete_count += 1
        
        # 更新表格
        self.update_tables()
        self.update_thumbnail_previews()
        self.log(f"已删除 {delete_count} 条句子（当前页）")

    def toggle_sentence_highlight(self, row, col):
        """切换句子高亮状态"""
        # 只处理第一列（高亮状态列）的点击
        if col != 0:
            return
        
        # 检查事件是否已被处理
        if hasattr(self, "_processing_sentence_highlight"):
            return
        self._processing_sentence_highlight = True
        
        try:
            # 获取当前颜色
            color = self.table_manager.sentence_color_edit.text()
            
            sentences = self.highlight_manager.get_current_page_sentences(self.page_index)
            if row < len(sentences):
                sent = sentences[row]
                if 'id' in sent:
                    if self.highlight_manager.is_sentence_highlighted(sent['id']):
                        self.highlight_manager.unhighlight_sentence(sent['id'])
                    else:
                        # 使用当前颜色设置
                        self.highlight_manager.highlight_sentence(sent['id'], self.page_index, color)
                    
                    # 更新表格
                    self.update_tables()
                    # 更新缩略图
                    self.update_thumbnail_previews()
        finally:
            # 确保标志被清除
            if hasattr(self, "_processing_sentence_highlight"):
                delattr(self, "_processing_sentence_highlight")

    # 导出功能
    def export_current_page_words(self):
        """导出当前页单词"""
        words = self.highlight_manager.translations['words'].get(self.page_index, {})
        ExportManager.export_words(words, self, all_pages=False)

    def export_all_pages_words(self):
        """导出所有页单词"""
        all_words = {}
        for page_words in self.highlight_manager.translations['words'].values():
            all_words.update(page_words)
        ExportManager.export_words(all_words, self, all_pages=True)

    def export_current_page_sentences(self):
        """导出当前页句子"""
        sentences = self.highlight_manager.get_current_page_sentences(self.page_index)
        ExportManager.export_sentences(sentences, self, all_pages=False)

    def export_all_sentences(self):
        """导出所有句子"""
        ExportManager.export_sentences(self.highlight_manager.translations['sentences'], self, all_pages=True)

    def handle_translate_sentences_result(self, sentences, page_index, task_type):
        """处理翻译结果 - 立即绘制高亮"""
        if not sentences:
            self.log("错误：翻译未返回任何内容")
            return
        
        # 添加翻译结果 - 使用高亮管理器的方法
        self.highlight_manager.add_sentences(sentences, page_index)
        
        # 立即高亮这些句子
        color = self.table_manager.sentence_color_edit.text()  # 获取当前句子颜色
        for sent in sentences:
            sent_id = sent.get('id')
            if sent_id:
                self.highlight_manager.highlight_sentence(sent_id, page_index, color)
        
        # 如果当前显示的是结果所在的页面，则更新表格和视图
        if self.page_index == page_index:
            self.update_tables()
            # 强制重绘当前页
            self.highlight_manager.draw_page_highlights(self.page_index)
        
        self.log(f"翻译完成，页面 {page_index + 1}，共 {len(sentences)} 个句子")
        self.cleanup_worker(id(self.sender()))

        self.highlight_manager.complete_translation_task(page_index)
        
        # 更新缩略图
        self.update_thumbnail_previews()

    def handle_extract_words_result(self, new_map, page_index, task_type):
        """处理单词提取结果 - 立即绘制高亮"""
        if not new_map:
            self.log("错误：生词提取未返回任何内容")
            return
        
        # 添加新单词
        for word, trans in new_map.items():
            self.highlight_manager.add_word_translation(word, trans, page_index)
        
        # 立即高亮这些单词
        color = self.table_manager.word_color_edit.text()  # 获取当前单词颜色
        for word in new_map:
            self.highlight_manager.highlight_word(word, page_index, color)
        
        # 如果当前显示的是结果所在的页面，则更新表格和视图
        if self.page_index == page_index:
            self.update_tables()
            # 强制重绘当前页
            self.highlight_manager.draw_page_highlights(self.page_index)
        
        self.log(f"生词提取完成，页面 {page_index + 1}，新增 {len(new_map)} 个单词")
        self.cleanup_worker(id(self.sender()))

        self.highlight_manager.complete_translation_task(page_index)
        
        # 更新缩略图
        self.update_thumbnail_previews()

    def handle_translation_error(self, error_msg):
        """处理翻译错误"""
        worker = self.sender()
        if worker:
            self.highlight_manager.complete_translation_task(worker.page_index)
            self.update_thumbnail_previews()
        self.log(f"错误: {error_msg}")
        self.cleanup_worker(id(self.sender()))

    def cancel_translation(self, worker_id):
        """取消翻译任务"""
        if worker_id in self.active_workers:
            worker, thread = self.active_workers[worker_id]
            worker.cancel()
            thread.quit()
            thread.wait()
            self.log(f"已取消任务 {worker_id}")
            self.cleanup_worker(worker_id)

    def cleanup_worker(self, worker_id):
        """清理工作线程"""
        if worker_id in self.active_workers:
            worker, thread = self.active_workers.pop(worker_id)
            thread.quit()
            thread.wait()
            thread.deleteLater()

    def update_selection_ui(self):
        """更新选择UI状态 - 暗黑模式友好版本"""
        # 获取选择信息的页面索引
        selection_page = self.selection_info.get("page_index")
        
        # 检查当前选择是否属于当前页面
        if self.is_dark_mode:
            # 暗黑模式下的颜色方案
            if selection_page is not None and selection_page == self.page_index:
                # 属于当前页面 - 深蓝色背景
                self.selection_box.setStyleSheet("background-color: #1a3d4c;")
                self.selection_page_label.setText(f"当前选择来自页面 {selection_page + 1}")
            elif selection_page is not None:
                # 不属于当前页面 - 深黄色背景
                self.selection_box.setStyleSheet("background-color: #4c3d1a;")
                self.selection_page_label.setText(
                    f"警告：当前选择来自页面 {selection_page + 1}，但您正在页面 {self.page_index + 1}"
                )
            else:
                # 没有选择 - 使用样式表默认颜色
                self.selection_box.setStyleSheet("")
                self.selection_page_label.setText("当前无选择")
        else:
            # 亮色模式下的颜色方案
            if selection_page is not None and selection_page == self.page_index:
                # 属于当前页面 - 正常显示
                self.selection_box.setStyleSheet("background-color: #e6f7ff;")
                self.selection_page_label.setText(f"当前选择来自页面 {selection_page + 1}")
            elif selection_page is not None:
                # 不属于当前页面 - 警告显示
                self.selection_box.setStyleSheet("background-color: #fff8e6;")
                self.selection_page_label.setText(
                    f"警告：当前选择来自页面 {selection_page + 1}，但您正在页面 {self.page_index + 1}"
                )
            else:
                # 没有选择
                self.selection_box.setStyleSheet("")
                self.selection_page_label.setText("当前无选择")

    def on_log_anchor_clicked(self, link):
        """处理日志中的链接点击事件"""
        if link.startswith("#cancel_"):
            worker_id = int(link.split("_")[1])
            self.cancel_translation(worker_id)

    def generate_thumbnails(self):
        """生成所有页面的缩略图（带高亮和状态指示器）"""
        self.thumbnails = []
        
        # 根据文档页数动态调整缩略图大小
        max_height = 160
        if self.doc.page_count > 50:
            max_height = 120
        self.thumbnail_size = (120, max_height)
        
        for page_num in range(self.doc.page_count):
            page = self.doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
            img = QtGui.QImage(pix.samples, pix.width, pix.height, 
                            pix.stride, QtGui.QImage.Format_RGB888)              
            pixmap = QtGui.QPixmap.fromImage(img)
            
            # 创建绘图设备
            painter = QtGui.QPainter(pixmap)
            
            # 绘制单词高亮
            if page_num in self.highlight_manager.page_highlights:
                page_data = self.highlight_manager.page_highlights[page_num]
                if 'words' in page_data:  # 确保有单词高亮数据
                    for word, word_info in page_data['words'].items():
                        if word_info.get('highlighted', False):
                            color = word_info['color']
                            for rect in word_info['rects']:
                                # 确保使用正确的坐标系统
                                # 注意：fitz.Rect 使用 PDF 坐标系统（原点在左上角）
                                scaled_rect = QtCore.QRectF(
                                    rect.x0 * 0.2,
                                    rect.y0 * 0.2,
                                    abs(rect.x1 - rect.x0) * 0.2,  # 宽度
                                    abs(rect.y1 - rect.y0) * 0.2   # 高度
                                )
                                painter.setBrush(QtGui.QBrush(color))
                                painter.setPen(QtGui.QPen(color.darker(120), 1))
                                painter.drawRect(scaled_rect)
            
            # 绘制句子高亮 - 使用正确的数据结构
            if page_num in self.highlight_manager.page_highlights:
                page_data = self.highlight_manager.page_highlights[page_num]
                if 'sentences' in page_data:  # 确保有句子高亮数据
                    for sent_id, sent_info in page_data['sentences'].items():
                        if sent_info.get('highlighted', False):
                            color = sent_info['color']
                            for rect in sent_info['rects']:
                                scaled_rect = QtCore.QRectF(
                                    rect.x0 * 0.2,
                                    rect.y0 * 0.2,
                                    abs(rect.x1 - rect.x0) * 0.2,
                                    abs(rect.y1 - rect.y0) * 0.2
                                )
                                painter.setBrush(QtGui.QBrush(color))
                                painter.setPen(QtGui.QPen(color.darker(120), 1))
                                painter.drawRect(scaled_rect)
            
            # === 修改：绘制状态指示器（在中央放大显示）===
            status = self.highlight_manager.get_page_translation_status(page_num)
            if status != 0:
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
                
                # 计算指示器位置（缩略图中央）
                indicator_size = 50  # 放大指示器大小
                indicator_x = (pixmap.width() - indicator_size) // 2
                indicator_y = (pixmap.height() - indicator_size) // 2
                
                # 创建半透明背景
                bg_rect = QtCore.QRectF(
                    indicator_x - 5, indicator_y - 5,
                    indicator_size + 10, indicator_size + 10
                )
                painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 180)))
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRoundedRect(bg_rect, 10, 10)
                
                if status == 1:  # 翻译中
                    # 绘制旋转的加载动画
                    painter.setPen(QtGui.QPen(QtGui.QColor(255, 200, 0), 4))
                    painter.setBrush(QtCore.Qt.NoBrush)
                    
                    # 计算旋转角度（基于时间）
                    angle = int(time.time() * 360) % 360
                    start_angle = angle * 16
                    span_angle = 270 * 16  # 3/4圆
                    
                    painter.drawArc(
                        indicator_x, indicator_y, 
                        indicator_size, indicator_size, 
                        start_angle, span_angle
                    )
                    
                    # 绘制加载文字（放大）
                    font = painter.font()
                    font.setPointSize(10)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.setPen(QtGui.QPen(QtGui.QColor(255, 200, 0)))
                    
                    # 获取活动任务数量
                    tasks = self.highlight_manager.page_translation_tasks.get(page_num, {'active': 0})
                    task_count = tasks['active']
                    text = f"加载中 ({task_count})"
                    
                    painter.drawText(
                        QtCore.QRectF(
                            indicator_x, indicator_y + indicator_size, 
                            indicator_size, 20
                        ),
                        QtCore.Qt.AlignCenter, text
                    )
                elif status == 2:  # 已完成
                    # 绘制绿色对勾
                    painter.setPen(QtGui.QPen(QtGui.QColor(0, 255, 0), 4))
                    painter.setBrush(QtCore.Qt.NoBrush)
                    
                    # 绘制对勾
                    check_size = indicator_size - 10
                    painter.drawLine(
                        indicator_x + 10, indicator_y + indicator_size//2,
                        indicator_x + indicator_size//2, indicator_y + indicator_size - 10
                    )
                    painter.drawLine(
                        indicator_x + indicator_size//2, indicator_y + indicator_size - 10,
                        indicator_x + indicator_size - 10, indicator_y + 10
                    )
                    
                    # 绘制完成文字（放大）
                    font = painter.font()
                    font.setPointSize(10)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.setPen(QtGui.QPen(QtGui.QColor(0, 255, 0)))
                    
                    # 获取已完成任务数量
                    tasks = self.highlight_manager.page_translation_tasks.get(page_num, {'completed': 0})
                    task_count = tasks['completed']
                    text = f"完成 ({task_count})"
                    
                    painter.drawText(
                        QtCore.QRectF(
                            indicator_x, indicator_y + indicator_size, 
                            indicator_size, 20
                        ),
                        QtCore.Qt.AlignCenter, text
                    )
            
            painter.end()
            
            # 调整到统一尺寸
            scaled_pixmap = pixmap.scaled(
                self.thumbnail_size[0], 
                self.thumbnail_size[1],
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.thumbnails.append(scaled_pixmap)

    def setup_thumbnail_dock(self):
        """设置缩略图预览dock（改进的抽屉效果）"""
        # 确保只创建一次
        if self.thumb_dock:
            return
        
        # 确保缩略图已生成
        if not hasattr(self, 'thumbnails') or not self.thumbnails:
            self.generate_thumbnails()
        
        # 重置缩略图标签列表
        self.thumbnail_labels = []
        
        # 创建主widget
        thumb_widget = QtWidgets.QWidget()
        thumb_layout = QtWidgets.QHBoxLayout(thumb_widget)
        thumb_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        thumb_layout.setSpacing(0)
        
        # 创建内容容器
        self.thumb_content = QtWidgets.QWidget()
        self.thumb_content_layout = QtWidgets.QVBoxLayout(self.thumb_content)
        self.thumb_content_layout.setContentsMargins(5, 5, 5, 5)
        self.thumb_content_layout.setAlignment(QtCore.Qt.AlignTop)
        
        # 标题
        title_label = QtWidgets.QLabel("页面预览")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.thumb_content_layout.addWidget(title_label)
        
        # 滚动区域
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        # 内容widget
        content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(content_widget)
        self.content_layout.setAlignment(QtCore.Qt.AlignTop)
        self.content_layout.setSpacing(5)
        
        # 添加所有缩略图
        for i, thumb in enumerate(self.thumbnails):
            # 创建缩略图标签
            thumb_label = QtWidgets.QLabel()
            thumb_label.setPixmap(thumb)
            thumb_label.setAlignment(QtCore.Qt.AlignCenter)
            thumb_label.setStyleSheet(
                "border: 1px solid #ccc; padding: 2px;"
                "margin: 2px; background: white;"
            )
            
            # 添加页码
            page_label = QtWidgets.QLabel(f"第 {i+1} 页")
            page_label.setAlignment(QtCore.Qt.AlignCenter)
            page_label.setStyleSheet("font-size: 10px;")
            
            # 容器
            container = QtWidgets.QWidget()
            container_layout = QtWidgets.QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(thumb_label)
            container_layout.addWidget(page_label)
            container_layout.setSpacing(0)
            
            # 设置点击事件
            container.mousePressEvent = lambda event, idx=i: self.on_thumbnail_clicked(idx)
            
            # 存储引用以便高亮当前页
            self.thumbnail_labels.append(container)
            
            self.content_layout.addWidget(container)
        
        scroll_area.setWidget(content_widget)
        self.thumb_content_layout.addWidget(scroll_area)
        
        # 添加内容到主布局
        thumb_layout.addWidget(self.thumb_content)
        
        # 创建展开/收起按钮容器
        self.toggle_button_container = QtWidgets.QWidget()
        self.toggle_button_container.setFixedWidth(20)
        self.toggle_button_container.setStyleSheet("background: #f0f0f0;")
        
        # 垂直布局用于居中按钮
        button_layout = QtWidgets.QVBoxLayout(self.toggle_button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        # 添加展开/收起按钮
        self.toggle_thumb_button = QtWidgets.QToolButton()
        self.toggle_thumb_button.setFixedSize(16, 16)
        self.toggle_thumb_button.setIcon(self.arrow_left)  # 使用创建的图标
        self.toggle_thumb_button.setStyleSheet("border: none; background: transparent;")
        self.toggle_thumb_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.toggle_thumb_button.setToolTip("收起预览栏")
        self.toggle_thumb_button.clicked.connect(self.toggle_thumbnail_dock)
        
        button_layout.addWidget(self.toggle_thumb_button, 0, QtCore.Qt.AlignCenter)
        
        # 添加按钮容器到主布局
        thumb_layout.addWidget(self.toggle_button_container)
        
        # 保存展开时的宽度
        self.expanded_width = self.thumbnail_size[0] + 90  # 缩略图宽度 + 边距
        
        # 创建dock
        self.thumb_dock = QtWidgets.QDockWidget("", self)  # 空标题
        self.thumb_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable)  # 允许关闭
        self.thumb_dock.setWidget(thumb_widget)
        self.thumb_dock.setTitleBarWidget(QtWidgets.QWidget())  # 隐藏默认标题栏
        
        # 设置dock的最小和最大宽度
        self.thumb_dock.setMinimumWidth(20)
        self.thumb_dock.setMaximumWidth(self.expanded_width)
        
        # 添加到左侧区域
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.thumb_dock)
        
        # 初始状态为展开
        self.thumb_dock_expanded = True
        self.thumb_dock.setFixedWidth(self.expanded_width)
        
        # 固定宽度，防止自动调整
        self.thumb_dock.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        # 初始化当前页高亮
        self.update_thumbnail_highlight()

    def on_thumbnail_clicked(self, page_index):
        """缩略图点击事件处理"""
        if page_index != self.page_index:
            self.page_index = page_index
            self.load_page()

    def update_thumbnail_highlight(self):
        """更新当前页缩略图的高亮状态"""
        # 确保缩略图标签已创建
        if not hasattr(self, 'thumbnail_labels') or not self.thumbnail_labels:
            return
        
        # 移除所有高亮
        for container in self.thumbnail_labels:
            container.setStyleSheet("")
        
        # 高亮当前页
        if self.page_index < len(self.thumbnail_labels):
            self.thumbnail_labels[self.page_index].setStyleSheet(
                "border: 2px solid #ff6600;"
            )

    def toggle_thumbnail_dock(self):
        """切换缩略图预览栏的展开/收起状态"""
        # 保存当前左侧dock的宽度
        current_left_width = self.left_dock.width()
        
        if self.thumb_dock_expanded:
            # 收起预览栏
            self.thumb_dock.setFixedWidth(20)
            self.thumb_content.hide()
            self.toggle_thumb_button.setIcon(self.arrow_right)  # 使用右箭头图标
            self.toggle_thumb_button.setToolTip("展开预览栏")
            self.thumb_dock_expanded = False
        else:
            # 展开预览栏
            self.thumb_dock.setFixedWidth(self.expanded_width)
            self.thumb_content.show()
            self.toggle_thumb_button.setIcon(self.arrow_left)  # 使用左箭头图标
            self.toggle_thumb_button.setToolTip("收起预览栏")
            self.thumb_dock_expanded = True
        
        # 立即恢复左侧dock的宽度
        self.left_dock.setFixedWidth(current_left_width)
        
        # 强制布局更新
        self.updateGeometry()

    def create_arrow_icons(self):
        """创建箭头图标资源"""
        # 创建左箭头图标
        pixmap_left = QtGui.QPixmap(16, 16)
        pixmap_left.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap_left)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtCore.Qt.darkGray, 2)
        painter.setPen(pen)
        painter.drawLine(12, 8, 4, 8)
        painter.drawLine(4, 8, 8, 4)
        painter.drawLine(4, 8, 8, 12)
        painter.end()
        self.arrow_left = QtGui.QIcon(pixmap_left)
        
        # 创建右箭头图标
        pixmap_right = QtGui.QPixmap(16, 16)
        pixmap_right.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap_right)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtCore.Qt.darkGray, 2)
        painter.setPen(pen)
        painter.drawLine(4, 8, 12, 8)
        painter.drawLine(12, 8, 8, 4)
        painter.drawLine(12, 8, 8, 12)
        painter.end()
        self.arrow_right = QtGui.QIcon(pixmap_right)

    def finalize_layout(self):
        """最终布局调整（确保所有尺寸正确计算）"""
        # 保存左侧dock的初始宽度
        self.saved_left_dock_width = self.left_dock.width()
        
        # 确保预览栏初始状态正确
        if self.thumb_dock_expanded:
            self.thumb_dock.setFixedWidth(self.expanded_width)
        else:
            self.thumb_dock.setFixedWidth(20)
        
        # 固定左侧dock的宽度
        self.left_dock.setFixedWidth(self.saved_left_dock_width)

    def setup_word_buttons(self):
        """连接单词按钮信号"""
        # 获取按钮引用
        btn_highlight_page = self.table_manager.btn_highlight_page_words
        btn_clear_page = self.table_manager.btn_clear_page_words
        btn_highlight_all = self.table_manager.btn_highlight_all_words
        btn_clear_all = self.table_manager.btn_clear_all_words  # 新按钮
        btn_color = self.table_manager.btn_word_color
        
        # 连接信号
        btn_highlight_page.clicked.connect(self.highlight_current_page_unhighlighted_words)
        btn_clear_page.clicked.connect(self.clear_current_page_word_highlights)
        btn_highlight_all.clicked.connect(self.highlight_all_pages_words)
        btn_clear_all.clicked.connect(self.clear_all_pages_word_highlights)  # 新功能
        btn_color.clicked.connect(lambda: self.choose_color("word"))
        self.table_manager.word_color_edit.textChanged.connect(
            lambda: self.update_color_button("word")
        )
        self.table_manager.btn_delete_selected_words.clicked.connect(self.delete_selected_words)

    def clear_all_pages_word_highlights(self):
        """清除所有页的单词高亮"""
        total = 0
        for page_index in list(self.highlight_manager.page_highlights.keys()):
            # 获取该页的所有单词
            if 'words' in self.highlight_manager.page_highlights[page_index]:
                words = list(self.highlight_manager.page_highlights[page_index]['words'].keys())
                for word in words:
                    if self.highlight_manager.unhighlight_word(word, page_index):
                        total += 1
        
        # 刷新当前页表格
        self.update_tables()
        self.update_thumbnail_previews()
        self.log(f"已清除所有页共 {total} 个单词高亮")

    def setup_sentence_buttons(self):
        """连接句子按钮信号"""
        # 获取按钮引用
        btn_highlight_page = self.table_manager.btn_highlight_page_sentences
        btn_clear_page = self.table_manager.btn_clear_page_sentences
        btn_highlight_all = self.table_manager.btn_highlight_all_sentences
        btn_clear_all = self.table_manager.btn_clear_all_sentences  # 新按钮
        btn_color = self.table_manager.btn_sentence_color
        
        # 连接信号
        btn_highlight_page.clicked.connect(self.highlight_current_page_unhighlighted_sentences)
        btn_clear_page.clicked.connect(self.clear_current_page_sentence_highlights)
        btn_highlight_all.clicked.connect(self.highlight_all_pages_sentences)
        btn_clear_all.clicked.connect(self.clear_all_pages_sentence_highlights)  # 新功能
        btn_color.clicked.connect(lambda: self.choose_color("sentence"))
        self.table_manager.sentence_color_edit.textChanged.connect(
            lambda: self.update_color_button("sentence")
        )

    def clear_all_pages_sentence_highlights(self):
        """清除所有页的句子高亮"""
        total = 0
        # 遍历所有句子
        for sent in self.highlight_manager.translations['sentences']:
            sent_id = sent.get('id')
            if sent_id:
                # 取消高亮句子
                if self.highlight_manager.unhighlight_sentence(sent_id):
                    total += 1
        
        # 刷新当前页表格
        self.update_tables()
        # 更新缩略图
        self.update_thumbnail_previews()
        self.log(f"已清除所有页共 {total} 个句子高亮")

    def highlight_current_page_unhighlighted_words(self):
        """高亮当前页所有未高亮的单词"""
        # 获取当前页的单词映射
        word_map = self.highlight_manager.translations['words'].get(self.page_index, {})
        
        # 获取当前页已高亮的单词
        highlighted_words = []
        if self.page_index in self.highlight_manager.page_highlights:
            page_data = self.highlight_manager.page_highlights[self.page_index]
            if 'words' in page_data:  # 确保有单词数据
                for word, word_info in page_data['words'].items():
                    if word_info.get('highlighted', False):
                        highlighted_words.append(word)
        
        # 获取当前颜色
        color = self.table_manager.word_color_edit.text()
        
        count = 0
        for word in word_map:
            if word not in highlighted_words:
                # 高亮单词 - 使用当前颜色
                if self.highlight_manager.highlight_word(word, self.page_index, color):
                    count += 1
        
        # 确保当前页的高亮全部绘制
        self.highlight_manager.draw_page_highlights(self.page_index)
        
        self.update_tables()
        
        # 刷新预览
        self.update_thumbnail_previews()
        self.log(f"已高亮 {count} 个未高亮单词")
    def clear_current_page_word_highlights(self):
        """清除当前页所有单词高亮"""
        # 使用新的 page_highlights 数据结构
        if self.page_index in self.highlight_manager.page_highlights:
            page_data = self.highlight_manager.page_highlights[self.page_index]
            words = list(page_data['words'].keys())
            
            # 使用新的 unhighlight_word 方法
            for word in words:
                self.highlight_manager.unhighlight_word(word, self.page_index)
            
            self.update_tables()
            self.update_thumbnail_previews()
            self.log(f"已清除当前页 {len(words)} 个单词高亮")

    def highlight_all_pages_words(self):
        """高亮所有页的单词"""
        # 获取当前颜色
        color = self.table_manager.word_color_edit.text()
        
        total = 0
        for page_index in self.highlight_manager.translations['words']:
            word_map = self.highlight_manager.translations['words'][page_index]
            for word in word_map:
                # 检查单词是否已高亮
                if not self.highlight_manager.is_word_highlighted(word, page_index):
                    # 高亮单词 - 使用当前颜色
                    if self.highlight_manager.highlight_word(word, page_index, color):
                        total += 1
        
        # 如果当前页有更新，刷新表格并绘制
        if self.page_index in self.highlight_manager.translations['words']:
            self.update_tables()
            # 强制绘制当前页
            self.highlight_manager.draw_page_highlights(self.page_index)

        self.update_thumbnail_previews()
        self.log(f"已高亮所有页共 {total} 个单词")

    def highlight_current_page_unhighlighted_sentences(self):
        """高亮当前页所有未高亮的句子"""
        # 获取当前页所有句子
        sentences = self.highlight_manager.get_current_page_sentences(self.page_index)
        
        # 获取当前页已高亮的句子ID
        highlighted_ids = []
        if self.page_index in self.highlight_manager.page_highlights:
            page_data = self.highlight_manager.page_highlights[self.page_index]
            if 'sentences' in page_data:  # 确保有句子数据
                for sent_id, sent_info in page_data['sentences'].items():
                    if sent_info.get('highlighted', False):
                        highlighted_ids.append(sent_id)
        
        # 获取当前颜色
        color = self.table_manager.sentence_color_edit.text()
        
        count = 0
        for sent in sentences:
            sent_id = sent.get('id')
            if sent_id and sent_id not in highlighted_ids:
                # 高亮句子 - 使用当前颜色
                if self.highlight_manager.highlight_sentence(sent_id, self.page_index, color):
                    count += 1
        
        self.update_tables()
        # 刷新预览 - 确保句子高亮显示在缩略图中
        self.update_thumbnail_previews()
        self.log(f"已高亮 {count} 个未高亮句子")

    def clear_current_page_sentence_highlights(self):
        """清除当前页所有句子高亮"""
        # 收集当前页所有句子ID
        sentences = self.highlight_manager.get_current_page_sentences(self.page_index)
        sent_ids = [sent.get('id') for sent in sentences]
        
        # 移除当前页所有句子高亮
        count = 0
        for sent_id in sent_ids:
            if sent_id and self.highlight_manager.unhighlight_sentence(sent_id):
                count += 1
        
        self.update_tables()
        self.update_thumbnail_previews()
        self.log(f"已清除当前页 {count} 个句子高亮")

    def highlight_all_pages_sentences(self):
        """高亮所有页的句子"""
        # 获取当前颜色
        color = self.table_manager.sentence_color_edit.text()
        
        total = 0
        for sent in self.highlight_manager.translations['sentences']:
            sent_id = sent.get('id')
            page_index = sent.get('page', self.page_index)
            if sent_id and not self.highlight_manager.is_sentence_highlighted(sent_id):
                # 高亮句子 - 使用当前颜色
                if self.highlight_manager.highlight_sentence(sent_id, page_index, color):
                    total += 1
        
        # 如果当前页有更新，刷新表格
        self.update_tables()
        
        # 刷新预览 - 确保句子高亮显示在缩略图中
        self.update_thumbnail_previews()
        self.log(f"已高亮所有页共 {total} 个句子")

    def delete_selected_words(self):
        """删除选中的单词"""
        rows_to_delete = sorted(
            [idx.row() for idx in self.table_manager.word_table.selectionModel().selectedRows()],
            reverse=True
        )
        
        delete_count = 0
        for row in rows_to_delete:
            word = self.table_manager.word_table.item(row, 1).text()
            
            # 移除单词
            self.highlight_manager.remove_word(word, self.page_index)
            delete_count += 1
        
        # 更新表格
        self.update_tables()
        self.update_thumbnail_previews()
        self.log(f"已删除 {delete_count} 个单词（当前页）")

    def export_highlighted_pdf(self):
        """导出带高亮的PDF文件（只在句子的首单词上标注翻译）"""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出带高亮PDF", "", "PDF Files (*.pdf)"
        )
        if not path:
            return
        
        # 创建新文档
        new_doc = fitz.open()
        
        # 复制每一页并添加高亮
        for page_num in range(self.doc.page_count):
            page = self.doc.load_page(page_num)
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(page.rect, self.doc, page_num)
            
            # 添加单词高亮（保持不变）
            if page_num in self.highlight_manager.page_highlights:
                page_data = self.highlight_manager.page_highlights[page_num]
                if 'words' in page_data:
                    for word, word_info in page_data['words'].items():
                        if word_info.get('highlighted', False):
                            color = word_info['color']
                            translation = word_info.get('translation', '')
                            
                            # 为每个单词矩形添加高亮和弹出式附注
                            for rect in word_info['rects']:
                                # 应用当前缩放比例
                                scaled_rect = rect * self.zoom
                                pdf_rect = fitz.Rect(
                                    scaled_rect.x0 / self.zoom,
                                    scaled_rect.y0 / self.zoom,
                                    scaled_rect.x1 / self.zoom,
                                    scaled_rect.y1 / self.zoom
                                )
                                
                                # 创建高亮注释
                                annot = new_page.add_highlight_annot(pdf_rect)
                                
                                # 设置颜色和透明度
                                annot.set_colors(stroke=[
                                    color.red()/255, 
                                    color.green()/255, 
                                    color.blue()/255
                                ])
                                annot.set_opacity(color.alpha()/255)
                                
                                # 添加翻译弹出式附注
                                if translation:
                                    # 设置弹出式附注信息
                                    annot.set_info(title="翻译", content=translation)
                                    
                                    # 设置弹出式附注位置
                                    popup_rect = fitz.Rect(
                                        pdf_rect.x0,
                                        pdf_rect.y0 - 20,
                                        pdf_rect.x0 + 150,
                                        pdf_rect.y0
                                    )
                                    annot.set_popup(popup_rect)
                                    
                                    # 设置背景色
                                    annot.set_colors(fill=[1, 1, 0.9])  # 淡黄色背景
                                
                                annot.update()
            
            # 修改：只在句子的首单词上添加翻译注释
            if page_num in self.highlight_manager.page_highlights:
                page_data = self.highlight_manager.page_highlights[page_num]
                if 'sentences' in page_data:
                    for sent_id, sent_info in page_data['sentences'].items():
                        if sent_info.get('highlighted', False):
                            color = sent_info['color']
                            translation = sent_info.get('translation', '')
                            
                            # 只处理第一个单词矩形（首单词）
                            if sent_info['rects']:  # 确保有矩形
                                rect = sent_info['rects'][0]  # 只取第一个矩形（首单词）
                                
                                # 应用当前缩放比例
                                scaled_rect = rect * self.zoom
                                pdf_rect = fitz.Rect(
                                    scaled_rect.x0 / self.zoom,
                                    scaled_rect.y0 / self.zoom,
                                    scaled_rect.x1 / self.zoom,
                                    scaled_rect.y1 / self.zoom
                                )
                                
                                # 创建高亮注释
                                annot = new_page.add_highlight_annot(pdf_rect)
                                
                                # 设置颜色和透明度
                                annot.set_colors(stroke=[
                                    color.red()/255, 
                                    color.green()/255, 
                                    color.blue()/255
                                ])
                                annot.set_opacity(color.alpha()/255)
                                
                                # 添加翻译弹出式附注
                                if translation:
                                    # 设置弹出式附注信息
                                    annot.set_info(title="翻译", content=translation)
                                    
                                    # 设置弹出式附注位置
                                    popup_rect = fitz.Rect(
                                        pdf_rect.x0,
                                        pdf_rect.y0 - 30,
                                        pdf_rect.x0 + 300,
                                        pdf_rect.y0
                                    )
                                    annot.set_popup(popup_rect)
                                    
                                    # 设置背景色
                                    annot.set_colors(fill=[1, 1, 0.9])  # 淡黄色背景
                                
                                annot.update()
        
        # 保存新文档
        new_doc.save(path)
        new_doc.close()
        self.log(f"已导出带高亮的PDF文件: {path}")

    def choose_color(self, color_type):
        """打开颜色对话框选择颜色"""
        # 获取当前颜色
        if color_type == "word":
            current_color = QtGui.QColor(self.table_manager.word_color_edit.text())
        else:
            current_color = QtGui.QColor(self.table_manager.sentence_color_edit.text())
        
        # 打开颜色对话框
        color = QtWidgets.QColorDialog.getColor(
            current_color, 
            self, 
            f"选择{color_type}高亮颜色"
        )
        
        if color.isValid():
            hex_color = color.name(QtGui.QColor.HexRgb)
            if color_type == "word":
                self.table_manager.word_color_edit.setText(hex_color)
                self.update_color_button("word")
            else:
                self.table_manager.sentence_color_edit.setText(hex_color)
                self.update_color_button("sentence")

    def update_color_button(self, color_type):
        """更新颜色按钮的背景色"""
        try:
            if color_type == "word":
                color_str = self.table_manager.word_color_edit.text()
                color = QtGui.QColor(color_str)
                self.table_manager.btn_word_color.setStyleSheet(
                    f"background-color: {color.name(QtGui.QColor.HexRgb)}; border: 1px solid #ccc;"
                )
            else:
                color_str = self.table_manager.sentence_color_edit.text()
                color = QtGui.QColor(color_str)
                self.table_manager.btn_sentence_color.setStyleSheet(
                    f"background-color: {color.name(QtGui.QColor.HexRgb)}; border: 1px solid #ccc;"
                )
        except:
            # 颜色格式错误时恢复默认
            if color_type == "word":
                self.table_manager.word_color_edit.setText("#FFFF00")
            else:
                self.table_manager.sentence_color_edit.setText("#ADD8E6")

    def update_thumbnail_previews(self):
        """更新缩略图预览（不重新创建整个dock）"""
        # 重新生成缩略图
        self.generate_thumbnails()
        
        # 更新现有缩略图显示
        for i, thumb in enumerate(self.thumbnails):
            if i < len(self.thumbnail_labels):
                # 获取缩略图容器
                container = self.thumbnail_labels[i]
                # 找到容器中的QLabel
                thumb_label = container.findChild(QtWidgets.QLabel)
                if thumb_label:
                    thumb_label.setPixmap(thumb)
        
        # 更新当前页高亮
        self.update_thumbnail_highlight()

    def toggle_dark_mode(self, checked):
        """切换日间/夜间模式（简化版）"""
        # 锁定布局更新
        self.setUpdatesEnabled(False)
        
        try:
            # 更新模式状态
            self.is_dark_mode = checked
            
            # 应用模式
            self.apply_dark_mode()
            
            # 更新按钮文本 - 使用更简洁的文本
            if hasattr(self, 'dark_mode_action'):
                if self.is_dark_mode:
                    self.dark_mode_action.setText("切换白天")
                else:
                    self.dark_mode_action.setText("切换暗黑")
            
            # 立即更新选择框的UI状态
            self.update_selection_ui()
            
            # 保存配置
            self.save_config()
        finally:
            # 解锁布局更新
            self.setUpdatesEnabled(True)
            self.updateGeometry()
    
    def toggle_invert_colors(self, checked):
        """切换PDF颜色翻转"""
        self.invert_pdf_colors = checked
        self.load_page()  # 重新加载当前页以应用颜色翻转
        self.save_config()  # 保存配置
    
    def apply_dark_mode(self):
        """应用暗黑模式样式表 - 恢复对比度功能"""
        # 应用主样式表
        if self.is_dark_mode:
            self.set_dark_theme()
        else:
            self.set_light_theme()
        
        # 更新按钮文本
        if hasattr(self, 'dark_mode_action'):
            if self.is_dark_mode:
                self.dark_mode_action.setText("切换白天")
            else:
                self.dark_mode_action.setText("切换暗黑")
        
        # 保留工具栏样式 - 恢复对比度功能的关键
        if hasattr(self, 'toolbar'):
            if self.is_dark_mode:
                # 暗黑模式工具栏样式
                self.toolbar.setStyleSheet("""
                    QToolBar {
                        background: #333337;
                        border: none;
                        padding: 2px;
                    }
                    QToolButton {
                        min-width: 90px;
                        min-height: 30px;
                        padding: 5px;
                        border: 1px solid #555555;
                        border-radius: 4px;
                        background: #3F3F46;
                        color: #FFFFFF;
                    }
                    QToolButton:hover {
                        background: #505059;
                    }
                    QToolButton:pressed {
                        background: #007ACC;
                    }
                    QToolButton::menu-button {
                        border: none;
                    }
                    QLabel {
                        padding: 0 5px;
                        color: #FFFFFF;
                    }
                    QSlider {
                        padding: 0 5px;
                    }
                """)
            else:
                # 白天模式工具栏样式
                self.toolbar.setStyleSheet("""
                    QToolBar {
                        background: #F0F0F0;
                        border: none;
                        padding: 2px;
                    }
                    QToolButton {
                        min-width: 90px;
                        min-height: 30px;
                        padding: 5px;
                        border: 1px solid #CCCCCC;
                        border-radius: 4px;
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #F6F7FA, stop:1 #DADBDE);
                    }
                    QToolButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #EBF4FD, stop:1 #D0E3FB);
                    }
                    QToolButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #D0E3FB, stop:1 #EBF4FD);
                    }
                    QToolButton::menu-button {
                        border: none;
                    }
                    QLabel {
                        padding: 0 5px;
                    }
                    QSlider {
                        padding: 0 5px;
                    }
                """)
            
            # 固定布局参数 - 解决间距问题
            self.toolbar.setContentsMargins(2, 2, 2, 2)
            if self.toolbar.layout():
                self.toolbar.layout().setSpacing(6)
                self.toolbar.layout().invalidate()
            
            # 强制调整大小
            self.toolbar.adjustSize()
        
        # 重新加载当前页面以应用对比度设置 - 关键步骤
        self.load_page()
        
        # 强制刷新所有UI元素
        if hasattr(self, 'selection_info'):
            self.update_selection_ui()
        if hasattr(self, 'highlight_manager'):
            self.highlight_manager.draw_page_highlights(self.page_index)
        if hasattr(self, 'update_thumbnail_previews'):
            self.update_thumbnail_previews()
        if hasattr(self, 'update_tables'):
            self.update_tables()
        if hasattr(self, 'view'):
            self.view.update()
        
        # 额外刷新 - 确保布局稳定
        QtCore.QTimer.singleShot(50, self.final_layout_refresh)
    
    def set_dark_theme(self):
        """设置暗黑模式样式表（简化版）"""
        dark_style = """
        /* 基础设置 */
        QWidget {
            background-color: #2D2D30;
            color: #F0F0F0;
        }
        QMainWindow, QDialog {
            background-color: #252526;
        }
        
        /* 文本编辑区域 */
        QTextEdit, QPlainTextEdit, QLineEdit {
            background-color: #1E1E1E;
            color: #DCDCDC;
            border: 1px solid #3F3F46;
        }
        
        /* 选择文本框 */
        #selection_box {
            background-color: #252526;
        }
        #log_text {
            background-color: #1A1A1A;
        }
        
        /* 标签页 */
        QTabWidget::pane {
            border: 1px solid #3F3F46;
            background: #252526;
        }
        QTabBar::tab {
            background: #2D2D30;
            color: #DCDCDC;
            padding: 5px 10px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            border: 1px solid #3F3F46;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background: #1E1E1E;
            color: #FFFFFF;
        }
        
        /* 表格样式 */
        QHeaderView::section {
            background-color: #3F3F46;
            color: #FFFFFF;
            padding: 4px;
            border: 1px solid #2D2D30;
        }
        QTableWidget {
            background-color: #1E1E1E;
            color: #DCDCDC;
            gridline-color: #3F3F46;
            alternate-background-color: #252526;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QTableWidget::item:selected {
            background-color: #007ACC;
            color: #FFFFFF;
        }
        
        /* Dock区域 */
        QDockWidget {
            titlebar-close-icon: url(none);
            titlebar-normal-icon: url(none);
            background: #252526;
        }
        QDockWidget::title {
            background: #3F3F46;
            padding: 4px;
            color: #FFFFFF;
        }
        
        /* 滚动条 */
        QScrollBar:vertical {
            background: #252526;
            width: 12px;
        }
        QScrollBar::handle:vertical {
            background: #3F3F46;
            min-height: 20px;
        }
        
        /* 状态栏 */
        QStatusBar {
            background: #333337;
            color: #F0F0F0;
        }
        
        /* 特定组件 */
        #page_label {
            background-color: #3F3F46;
            color: #FFFFFF;
            border: 1px solid #2D2D30;
            padding: 2px 8px;
            border-radius: 3px;
        }
        """
        self.setStyleSheet(dark_style)
    
    def set_light_theme(self):
        """设置日间模式样式表（简化版）"""
        light_style = """
        /* 基础设置 */
        QWidget {
            background-color: #F0F0F0;
            color: #000000;
        }
        QMainWindow, QDialog {
            background-color: #FFFFFF;
        }
        
        QTextEdit, QPlainTextEdit, QLineEdit {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
        }
        
        #log_text {
            background-color: #FFFFFF;
            color: #000000;
        }
        
        #page_label {
            background-color: #F0F0F0;
            color: #000000;
            border: 1px solid #CCCCCC;
            padding: 2px 8px;
            border-radius: 3px;
        }
        
        /* 表格样式 */
        QHeaderView::section {
            background-color: #E0E0E0;
            color: #000000;
            padding: 4px 8px;
            border: 1px solid #CCCCCC;
            font-weight: bold;
        }
        QTableWidget {
            background-color: #FFFFFF;
            color: #000000;
            gridline-color: #CCCCCC;
            alternate-background-color: #F8F8F8;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QTableWidget::item:selected {
            background-color: #B8D6FF;
            color: #000000;
        }
        """
        self.setStyleSheet(light_style)
    
    def setup_dark_mode(self):
        """初始化暗黑模式设置"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'ui.cfg')
            if not os.path.exists(config_path):
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'ui.cfg')
            
            with open(config_path) as f:
                config = json.load(f)
                self.is_dark_mode = config.get("DARK_MODE", False)
                self.invert_pdf_colors = config.get("INVERT_PDF", False)
                self.contrast_level = config.get("CONTRAST_LEVEL", 0.7)
        except:
            self.is_dark_mode = False
            self.invert_pdf_colors = False
            self.contrast_level = 0.7
        
        # 应用模式
        self.apply_dark_mode()
        
        # 设置按钮初始文本
        if hasattr(self, 'dark_mode_action'):
            if self.is_dark_mode:
                self.dark_mode_action.setText("切换暗黑")
            else:
                self.dark_mode_action.setText("切换白天")
        
        # 确保翻转效果立即应用 - 新增
        if self.invert_pdf_colors:
            self.load_page()  # 强制重新加载当前页面以应用颜色翻转
    
    def save_config(self):
        """保存当前配置到文件"""
        config = {
            "DARK_MODE": self.is_dark_mode,
            "INVERT_PDF": self.invert_pdf_colors,
            "CONTRAST_LEVEL": self.contrast_level  # 新增
        }
        
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'ui.cfg')
            if not os.path.exists(config_path):
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'ui.cfg')
            
            # 保留原有配置，只更新我们的设置
            existing_config = {}
            if os.path.exists(config_path):
                with open(config_path) as f:
                    existing_config = json.load(f)
            
            # 合并配置
            existing_config.update(config)
            
            with open(config_path, 'w') as f:
                json.dump(existing_config, f, indent=4)
        except Exception as e:
            print(f"保存配置失败: {str(e)}")

    def set_contrast_level(self, value):
        """设置对比度级别"""
        self.contrast_level = value / 100.0
        # 立即应用对比度更改
        if self.invert_pdf_colors:
            self.load_page()
        self.save_config()

    def sync_ui_states(self):
        """同步UI元素状态"""
        # 暗黑模式按钮
        if hasattr(self, 'dark_mode_action'):
            self.dark_mode_action.setChecked(self.is_dark_mode)
            # 统一初始文本设置
            if self.is_dark_mode:
                self.dark_mode_action.setText("切换白天")
            else:
                self.dark_mode_action.setText("切换暗黑")
        
        # 翻转PDF按钮
        if hasattr(self, 'invert_action'):
            self.invert_action.setChecked(self.invert_pdf_colors)
            self.invert_action.setText("翻转PDF颜色")  # 确保文本一致
        
        # 对比度滑块
        if hasattr(self, 'contrast_slider'):
            self.contrast_slider.setValue(int(self.contrast_level * 100))

    def final_layout_refresh(self):
        """最终布局刷新 - 确保间距稳定"""
        if hasattr(self, 'toolbar') and self.toolbar:
            self.toolbar.updateGeometry()
            self.toolbar.adjustSize()

    def get_selection_with_context(self):
        """获取带上下文的文本以改善句子匹配"""
        if not self.selection_info:
            return ""
        
        # 获取当前页面和选择矩形
        page_index = self.selection_info.get("page_index", self.page_index)
        page = self.doc[page_index]
        
        # 获取选择周围的文本（扩大区域）
        context_rect = fitz.Rect(
            self.selection_info.get("rect", {}).get("x0", 0) - 30,
            self.selection_info.get("rect", {}).get("y0", 0) - 15,
            self.selection_info.get("rect", {}).get("x1", 0) + 30,
            self.selection_info.get("rect", {}).get("y1", 0) + 15
        )
        
        # 确保矩形在页面范围内
        page_rect = page.rect
        context_rect.x0 = max(context_rect.x0, page_rect.x0)
        context_rect.y0 = max(context_rect.y0, page_rect.y0)
        context_rect.x1 = min(context_rect.x1, page_rect.x1)
        context_rect.y1 = min(context_rect.y1, page_rect.y1)
        
        return clean_text(page.get_textbox(context_rect))
