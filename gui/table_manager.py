from PyQt5 import QtWidgets, QtCore, QtGui  # 添加 QtGui 导入

class TableManager:
    def __init__(self, highlight_manager):
        self.highlight_manager = highlight_manager
        
        # 创建单词表格的按钮容器
        self.word_button_container = QtWidgets.QWidget()
        word_btn_layout = QtWidgets.QHBoxLayout(self.word_button_container)
        
        # 单词表格按钮
        self.btn_highlight_page_words = QtWidgets.QPushButton("一键高亮")
        self.btn_clear_page_words = QtWidgets.QPushButton("一键清除")
        self.btn_highlight_all_words = QtWidgets.QPushButton("高亮所有页")
        self.btn_clear_all_words = QtWidgets.QPushButton("清除所有页")
        self.btn_delete_selected_words = QtWidgets.QPushButton("删除选中")
        
        # 颜色选择控件
        self.word_color_label = QtWidgets.QLabel("单词颜色:")
        self.word_color_edit = QtWidgets.QLineEdit("#FFFF00")
        self.word_color_edit.setFixedWidth(70)
        self.btn_word_color = QtWidgets.QPushButton()
        self.btn_word_color.setFixedSize(20, 20)
        self.btn_word_color.setStyleSheet("background-color: #FFFF00; border: 1px solid #ccc;")
        
        # 添加到布局
        word_btn_layout.addWidget(self.btn_highlight_page_words)
        word_btn_layout.addWidget(self.btn_clear_page_words)
        word_btn_layout.addWidget(self.btn_highlight_all_words)
        word_btn_layout.addWidget(self.btn_clear_all_words)
        word_btn_layout.addWidget(self.btn_delete_selected_words)
        word_btn_layout.addWidget(self.word_color_label)
        word_btn_layout.addWidget(self.word_color_edit)
        word_btn_layout.addWidget(self.btn_word_color)
        
        # 创建句子表格的按钮容器
        self.sentence_button_container = QtWidgets.QWidget()
        sentence_btn_layout = QtWidgets.QHBoxLayout(self.sentence_button_container)
        
        # 句子表格按钮
        self.btn_highlight_page_sentences = QtWidgets.QPushButton("一键高亮")
        self.btn_clear_page_sentences = QtWidgets.QPushButton("一键清除")
        self.btn_highlight_all_sentences = QtWidgets.QPushButton("高亮所有页")
        self.btn_clear_all_sentences = QtWidgets.QPushButton("清除所有页")
        
        # 颜色选择控件
        self.sentence_color_label = QtWidgets.QLabel("句子颜色:")
        self.sentence_color_edit = QtWidgets.QLineEdit("#ADD8E6")
        self.sentence_color_edit.setFixedWidth(70)
        self.btn_sentence_color = QtWidgets.QPushButton()
        self.btn_sentence_color.setFixedSize(20, 20)
        self.btn_sentence_color.setStyleSheet("background-color: #ADD8E6; border: 1px solid #ccc;")
        
        # 添加到布局
        sentence_btn_layout.addWidget(self.btn_highlight_page_sentences)
        sentence_btn_layout.addWidget(self.btn_clear_page_sentences)
        sentence_btn_layout.addWidget(self.btn_highlight_all_sentences)
        sentence_btn_layout.addWidget(self.btn_clear_all_sentences)
        sentence_btn_layout.addWidget(self.sentence_color_label)
        sentence_btn_layout.addWidget(self.sentence_color_edit)
        sentence_btn_layout.addWidget(self.btn_sentence_color)
        
        # 单词表格
        self.word_table = QtWidgets.QTableWidget(0, 3)
        self.word_table.setHorizontalHeaderLabels(["✔", "Word", "Translation"])
        self.word_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.word_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.word_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        hdr = self.word_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        
        # 句子表格
        self.sentence_table = QtWidgets.QTableWidget(0, 3)
        self.sentence_table.setHorizontalHeaderLabels(["✓", "Original", "Translation"])
        self.sentence_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.sentence_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.sentence_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        hdr = self.sentence_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

    def populate_word_table(self, word_map, highlighted_words):
        """填充单词表格"""
        self.word_table.clearContents()
        self.word_table.setRowCount(0)
        
        for w, t in word_map.items():
            r = self.word_table.rowCount()
            self.word_table.insertRow(r)
            
            # 高亮状态
            is_hl = w in highlighted_words
            st = QtWidgets.QTableWidgetItem("✔" if is_hl else "")
            st.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            
            # 单词
            wi = QtWidgets.QTableWidgetItem(w)
            wi.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            
            # 翻译
            ti = QtWidgets.QTableWidgetItem(t)
            ti.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            
            self.word_table.setItem(r, 0, st)
            self.word_table.setItem(r, 1, wi)
            self.word_table.setItem(r, 2, ti)
            
            # 设置行高亮状态（使用动态属性而不是直接设置背景色）
            if is_hl:
                for col in range(3):
                    item = self.word_table.item(r, col)
                    if item:
                        # 使用动态属性标记高亮状态
                        item.setData(QtCore.Qt.UserRole, "word-highlighted")
    def populate_sentence_table(self, sentences, highlighted_ids):
        """填充句子表格"""
        self.sentence_table.clearContents()
        self.sentence_table.setRowCount(0)
        
        for i, sent in enumerate(sentences):
            r = self.sentence_table.rowCount()
            self.sentence_table.insertRow(r)
            
            # 高亮状态
            is_hl = sent.get('id') in highlighted_ids
            hl_item = QtWidgets.QTableWidgetItem("✓" if is_hl else "")
            hl_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            
            # 原句
            orig_item = QtWidgets.QTableWidgetItem(sent['original'])
            orig_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            
            # 翻译
            trans_item = QtWidgets.QTableWidgetItem(sent['translation'])
            trans_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            
            self.sentence_table.setItem(r, 0, hl_item)
            self.sentence_table.setItem(r, 1, orig_item)
            self.sentence_table.setItem(r, 2, trans_item)
            
            # 设置行高亮状态（使用动态属性而不是直接设置背景色）
            if is_hl:
                for col in range(3):
                    item = self.sentence_table.item(r, col)
                    if item:
                        # 使用动态属性标记高亮状态
                        item.setData(QtCore.Qt.UserRole, "sentence-highlighted")

        def delete_selected_words(self):
            """删除选中的单词"""
            # 这个方法将在 main_window.py 中实现
            pass