import csv
import re
from PyQt5 import QtWidgets
import unicodedata

def export_to_csv(data, file_path, parent=None):
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["Word", "Translation"])
            for w, t in data.items():
                writer.writerow([w, t])
        return True, len(data)
    except Exception as e:
        if parent:
            QtWidgets.QMessageBox.warning(parent, "Export Error", str(e))
        return False, 0

def export_sentences_to_csv(sentences, file_path, parent=None):
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["Original", "Translation"])
            for sent in sentences:
                writer.writerow([sent['original'], sent['translation']])
        return True, len(sentences)
    except Exception as e:
        if parent:
            QtWidgets.QMessageBox.warning(parent, "Export Error", str(e))
        return False, 0

def clean_text(text):
    """清理文本：移除多余空格和换行符，保留基本标点"""
    # 替换各种换行符为空格
    text = re.sub(r'[\n\r\t]+', ' ', text)
    
    # 合并多个连续空格
    text = re.sub(r'\s{2,}', ' ', text)
    
    # 移除开头和结尾的空格
    text = text.strip()
    
    # 处理常见的OCR错误
    text = re.sub(r'\s*([.,;:!?])\s*', r'\1 ', text)  # 标点符号后的空格
    text = re.sub(r'\s+-\s+', '-', text)  # 连字符
    
    # 处理引用标记 [1] 等
    text = re.sub(r'\s*\[\d+\]\s*', ' ', text)
    
    return text
def calculate_word_similarity(word1, word2):
    """计算两个单词的相似度（0.0-1.0）使用改进的编辑距离 - 增强版"""
    # 添加Unicode规范化
    word1 = unicodedata.normalize('NFKD', word1).encode('ascii', 'ignore').decode('ascii')
    word2 = unicodedata.normalize('NFKD', word2).encode('ascii', 'ignore').decode('ascii')
    
    # 如果完全匹配，返回1.0
    if word1 == word2:
        return 1.0
    
    # 处理复数形式和所有格
    if word1.endswith("s") and word1[:-1] == word2:
        return 0.95
    if word2.endswith("s") and word2[:-1] == word1:
        return 0.95
    if word1.endswith("'s") and word1[:-2] == word2:
        return 0.95
    if word2.endswith("'s") and word2[:-2] == word1:
        return 0.95
    
    # 处理跨行连字符情况
    if '-' in word1 and word1.replace('-', '') == word2:
        return 0.92
    if '-' in word2 and word2.replace('-', '') == word1:
        return 0.92
    
    # 计算编辑距离
    len1, len2 = len(word1), len(word2)
    max_len = max(len1, len2)
    
    # 如果长度差异太大，相似度低
    if abs(len1 - len2) / max_len > 0.4:
        return 0.0
    
    # 创建DP表
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    # 初始化边界条件
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    
    # 填充DP表
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if word1[i-1] == word2[j-1] else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,    # 删除
                dp[i][j-1] + 1,    # 插入
                dp[i-1][j-1] + cost # 替换
            )
    
    # 计算相似度
    distance = dp[len1][len2]
    similarity = 1.0 - (distance / max_len)
    
    # 提高常见错误模式的相似度
    if distance == 1:
        # 单字符差异
        if len1 == len2:
            # 检查元音替换 (e.g., color/colour)
            vowels = "aeiou"
            diff_pos = [k for k in range(len1) if word1[k] != word2[k]][0]
            if word1[diff_pos] in vowels and word2[diff_pos] in vowels:
                similarity = min(1.0, similarity + 0.2)
    
    return max(0.0, min(1.0, similarity))