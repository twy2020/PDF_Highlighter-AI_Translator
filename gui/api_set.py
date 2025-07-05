# api_set.py - API设置模块
import json
import os
import requests
from PyQt5 import QtWidgets, QtCore

class ApiSetPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_config()  # 确保在初始化时加载配置
    
    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # API设置标签
        label = QtWidgets.QLabel("API设置")
        label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(label)
        
        # 表单布局
        form = QtWidgets.QFormLayout()
        self.api_url_edit = QtWidgets.QLineEdit()
        self.api_key_edit = QtWidgets.QLineEdit()
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.model_name_edit = QtWidgets.QLineEdit()
        self.timeout_edit = QtWidgets.QSpinBox()
        self.timeout_edit.setRange(10, 300)
        
        form.addRow("API URL:", self.api_url_edit)
        form.addRow("API Key:", self.api_key_edit)
        form.addRow("Model Name:", self.model_name_edit)
        form.addRow("Timeout (秒):", self.timeout_edit)
        
        layout.addLayout(form)
        
        # 按钮布局
        btn_layout = QtWidgets.QHBoxLayout()
        test_btn = QtWidgets.QPushButton("测试连接")
        save_btn = QtWidgets.QPushButton("保存设置")
        btn_layout.addWidget(test_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        # 状态标签
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        # 连接信号
        test_btn.clicked.connect(self.test_connection)
        save_btn.clicked.connect(self.save_config)
    
    def load_config(self):
        """从ai.cfg加载API配置"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'ai.cfg')
            if not os.path.exists(config_path):
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'ai.cfg')
            
            with open(config_path) as f:
                config = json.load(f)
                self.api_url_edit.setText(config.get("API_URL", ""))
                self.api_key_edit.setText(config.get("API_KEY", ""))
                self.model_name_edit.setText(config.get("MODEL_NAME", ""))
                self.timeout_edit.setValue(config.get("REQUEST_TIMEOUT", 60))
                self.status_label.setText("配置加载成功")
        except Exception as e:
            self.status_label.setText(f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存API配置到ai.cfg"""
        config = {
            "API_URL": self.api_url_edit.text(),
            "API_KEY": self.api_key_edit.text(),
            "MODEL_NAME": self.model_name_edit.text(),
            "REQUEST_TIMEOUT": self.timeout_edit.value()
        }
        
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'ai.cfg')
            if not os.path.exists(config_path):
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'ai.cfg')
            
            # 保留原有配置，只更新API设置
            existing_config = {}
            if os.path.exists(config_path):
                with open(config_path) as f:
                    existing_config = json.load(f)
            
            # 合并配置 - 只更新API相关设置
            existing_config.update(config)
            
            with open(config_path, 'w') as f:
                json.dump(existing_config, f, indent=4)
            self.status_label.setText("API配置保存成功！")
        except Exception as e:
            self.status_label.setText(f"保存API配置失败: {str(e)}")
    
    def test_connection(self):
        url = self.api_url_edit.text()
        api_key = self.api_key_edit.text()
        model = self.model_name_edit.text()
        
        if not url or not api_key or not model:
            self.status_label.setText("请填写完整的配置信息")
            return
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Say 'test'"}],
            "max_tokens": 5
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                self.status_label.setText("连接成功！")
            else:
                self.status_label.setText(f"连接失败: {response.status_code} - {response.reason}")
        except Exception as e:
            self.status_label.setText(f"连接错误: {str(e)}")

class PromptSetPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_config()  # 确保在初始化时加载配置
    
    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Prompt设置标签
        label = QtWidgets.QLabel("生词提取Prompt设置")
        label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(label)
        
        # 提示信息
        hint_label = QtWidgets.QLabel("设置提取生词的条件（例如：初中水平以上、生词、难词、专业用词、冷门词组、重点词等）")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(hint_label)
        
        # 表单布局
        form = QtWidgets.QFormLayout()
        
        # 生词提取条件设置
        self.word_prompt_edit = QtWidgets.QLineEdit()
        self.word_prompt_edit.setPlaceholderText("例如：初中水平以上的生词、难词、专业用词、冷门词组和重点词")
        
        form.addRow("提取条件:", self.word_prompt_edit)
        layout.addLayout(form)
        
        # 按钮布局
        btn_layout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("保存设置")
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        # 状态标签
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        # 连接信号
        save_btn.clicked.connect(self.save_config)
    
    def load_config(self):
        """从ai.cfg加载Prompt配置"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'ai.cfg')
            if not os.path.exists(config_path):
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'ai.cfg')
            
            with open(config_path) as f:
                config = json.load(f)
                self.word_prompt_edit.setText(config.get("WORD_PROMPT", ""))
                self.status_label.setText("Prompt配置加载成功")
        except Exception as e:
            self.status_label.setText(f"加载Prompt配置失败: {str(e)}")
    
    def save_config(self):
        """保存Prompt配置到ai.cfg"""
        word_prompt = self.word_prompt_edit.text().strip()
        if not word_prompt:
            self.status_label.setText("提示词不能为空")
            return
        
        config = {
            "WORD_PROMPT": word_prompt
        }
        
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'ai.cfg')
            if not os.path.exists(config_path):
                parent_dir = os.path.dirname(current_dir)
                config_path = os.path.join(parent_dir, 'ai.cfg')
            
            # 保留原有配置，只更新Prompt设置
            existing_config = {}
            if os.path.exists(config_path):
                with open(config_path) as f:
                    existing_config = json.load(f)
            
            # 合并配置 - 只更新Prompt设置
            existing_config.update(config)
            
            with open(config_path, 'w') as f:
                json.dump(existing_config, f, indent=4)
            self.status_label.setText("Prompt配置保存成功！")
        except Exception as e:
            self.status_label.setText(f"保存Prompt配置失败: {str(e)}")
    
    