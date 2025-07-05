import json
import requests
import os
import re  # 添加缺失的导入
import fitz
import numpy as np
import unicodedata
from math import exp
from PyQt5 import QtWidgets
from utils import clean_text, calculate_word_similarity

def load_ai_config():
    """从ai.cfg加载API配置"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'ai.cfg')
        
        if not os.path.exists(config_path):
            parent_dir = os.path.dirname(current_dir)
            config_path = os.path.join(parent_dir, 'ai.cfg')
        
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        # 返回默认值作为备用
        return {
            "API_URL": "https://api.siliconflow.cn/v1/chat/completions",
            "API_KEY": "sk-lrqadizsgudymkesgkcfzaxlyqdjmdogmrewslzbxoqxaotm",
            "MODEL_NAME": "deepseek-ai/DeepSeek-V3",
            "REQUEST_TIMEOUT": 60
        }
def translate_sentences(text, parent=None):
    """翻译整段文本并分句 - 使用固定prompt"""
    config = load_ai_config()
    headers = {
        "Authorization": f"Bearer {config['API_KEY']}",
        "Content-Type": "application/json"
    }
    
    # 清理文本
    cleaned_text = clean_text(text)
    
    # 固定句子翻译prompt
    fixed_sentence_prompt = (
        "你是一名英语专家，请将以下英文文本按句子分割，并逐句翻译成中文。"
        "返回一个JSON数组，数组的每个元素是一个对象，包含两个字段：\"original\"和\"translation\"。"
        "不要返回其他任何内容。文本如下：\n"
    )
    
    payload = {
        "model": config["MODEL_NAME"],
        "messages": [{
            "role": "user",
            "content": fixed_sentence_prompt + cleaned_text
        }]
    }
    
    try:
        r = requests.post(
            config["API_URL"],
            json=payload,
            headers=headers,
            timeout=config["REQUEST_TIMEOUT"]
        )
        r.raise_for_status()
        cont = r.json()["choices"][0]["message"]["content"]
        
        # 解析JSON数组
        start = cont.find("[")
        end = cont.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError("Response does not contain a valid JSON array")
        return json.loads(cont[start:end])
    except Exception as e:
        if parent:
            QtWidgets.QMessageBox.warning(parent, "Translation Error", str(e))
        return []

def extract_and_translate_words(text, parent=None):
    """提取并翻译生词 - 使用用户设置的提取条件"""
    config = load_ai_config()
    headers = {
        "Authorization": f"Bearer {config['API_KEY']}",
        "Content-Type": "application/json"
    }
    
    # 清理文本
    cleaned_text = clean_text(text)
    
    # 获取用户设置的提取条件，如果没有则使用默认值
    word_prompt = config.get("WORD_PROMPT", "初中水平以上的生词、难词、专业用词、冷门词组和重点词")
    
    # 组合完整的prompt
    full_word_prompt = (
        f"你是一名英语专家，请根据下面提供的文本，找出所有{word_prompt}。"
        "按照词组/单词：翻译的格式返回 JSON {word:translation}，禁止返回其他任何文本：\n"
    )
    
    payload = {
        "model": config["MODEL_NAME"],
        "messages": [{
            "role": "user",
            "content": full_word_prompt + cleaned_text
        }]
    }
    
    try:
        r = requests.post(
            config["API_URL"],
            json=payload,
            headers=headers,
            timeout=config["REQUEST_TIMEOUT"]
        )
        r.raise_for_status()
        cont = r.json()["choices"][0]["message"]["content"]
        json_start = cont.find("{")
        json_end = cont.rfind("}") + 1
        return json.loads(cont[json_start:json_end])
    except Exception as e:
        if parent:
            QtWidgets.QMessageBox.warning(parent, "Translation Error", str(e))
        return {}
    
def clean_word(w):
    """
    清理单词：移除非字母数字字符，保留连字符、撇号和基本标点，
    同时规范化Unicode字符，特别优化跨行单词处理
    """
    # 规范化Unicode：将特殊字符转换为基础形式
    w = unicodedata.normalize('NFKD', w).encode('ascii', 'ignore').decode('ascii')
    
    # 特殊处理跨行连字符情况
    # 如果单词以连字符开头（可能是跨行单词的第二部分）
    if w.startswith(('-', '‐', '‑', '–', '—')) and len(w) > 1:
        w = w[1:]  # 移除开头的连字符
    
    # 保留字母、数字、连字符、撇号和基本标点
    # 注意：保留多种连字符类型以便后续处理
    cleaned = ''.join(
        c for c in w 
        if c.isalnum() or c in ['-', '‐', '‑', '–', '—', "'", '.', ',', ';', ':', '!', '?']
    ).lower()
    
    # 处理常见的OCR错误
    # 移除结尾的连字符（跨行单词的第一部分）
    if cleaned.endswith(('-', '‐', '‑', '–', '—')):
        cleaned = cleaned[:-1]
    
    # 统一各种连字符为普通连字符
    cleaned = cleaned.replace('‐', '-').replace('‑', '-').replace('–', '-').replace('—', '-')
    
    # 处理常见缩写
    if cleaned == "dont": cleaned = "don't"
    elif cleaned == "cant": cleaned = "can't"
    elif cleaned == "wont": cleaned = "won't"
    elif cleaned == "isnt": cleaned = "isn't"
    elif cleaned == "wasnt": cleaned = "wasn't"
    elif cleaned == "doesnt": cleaned = "doesn't"
    elif cleaned == "couldnt": cleaned = "couldn't"
    elif cleaned == "shouldnt": cleaned = "shouldn't"
    elif cleaned == "wouldnt": cleaned = "wouldn't"
    elif cleaned == "arent": cleaned = "aren't"
    elif cleaned == "havent": cleaned = "haven't"
    
    # 特殊处理跨行单词的常见情况
    # 如果单词以连字符结尾（跨行单词的第一部分）
    if cleaned.endswith('-') and len(cleaned) > 1:
        # 保留单词主体部分（去除连字符）
        cleaned = cleaned[:-1]
    
    return cleaned
def find_word_in_page(page, word):
    """查找单词在页面中的位置，处理被拆分的单词 - 改进版"""
    # 清理目标单词
    target_word = clean_word(word)
    
    # 获取页面所有单词及其位置
    page_words = page.get_text("words")
    if not page_words:
        return []
    
    # 创建页面单词列表，合并被连字符拆分的单词
    cleaned_page_words = []
    i = 0
    while i < len(page_words):
        text = page_words[i][4]
        rect = fitz.Rect(page_words[i][:4])
        
        # 检查当前单词是否以连字符结尾 - 新增：支持多种连字符类型
        if i < len(page_words) - 1:
            next_text = page_words[i+1][4]
            
            # 检查连字符情况（包括软连字符和普通连字符）
            has_hyphen = (
                text.endswith('-') or 
                text.endswith('‐') or  # U+2010 连字符
                text.endswith('‑') or  # U+2011 不间断连字符
                text.endswith('–') or  # U+2013 短破折号
                text.endswith('—')     # U+2014 长破折号
            )
            
            # 改进：检查下一个单词是否以当前单词结尾开始
            if has_hyphen and next_text:
                # 尝试合并单词
                base_word = text.rstrip('‐‑–—')  # 移除所有类型的连字符
                
                # 检查合并后的单词是否更接近目标单词
                merged_word = base_word + next_text
                merged_cleaned = clean_word(merged_word)
                
                # 计算相似度
                original_sim = calculate_word_similarity(target_word, clean_word(text))
                merged_sim = calculate_word_similarity(target_word, merged_cleaned)
                
                # 如果合并后相似度更高，则合并单词
                if merged_sim > original_sim and merged_sim > 0.7:
                    # 合并单词
                    text = merged_word
                    # 合并矩形
                    rect = rect | fitz.Rect(page_words[i+1][:4])
                    # 跳过下一个单词
                    i += 1
        
        # 清理单词（移除非字母数字字符并转为小写）
        cleaned = clean_word(text)
        if cleaned:  # 跳过空单词
            cleaned_page_words.append({
                "text": text,
                "cleaned": cleaned,
                "rect": rect
            })
        i += 1
    
    # 查找匹配的单词
    matches = []
    for page_word in cleaned_page_words:
        if page_word["cleaned"] == target_word:
            matches.append(page_word["rect"])
    
    # 改进：如果没有找到精确匹配，尝试模糊匹配
    if not matches:
        best_sim = 0
        best_match = None
        for page_word in cleaned_page_words:
            sim = calculate_word_similarity(target_word, page_word["cleaned"])
            if sim > best_sim and sim > 0.8:  # 相似度阈值设为80%
                best_sim = sim
                best_match = page_word["rect"]
        
        if best_match:
            matches.append(best_match)
    
    return matches

def find_sentence_in_page(page, sentence_text):
    """使用动态规划的局部序列对齐算法定位句子"""
    print(f"\n===== 开始查找句子: '{sentence_text}' =====")
    
    # 清理句子文本
    cleaned_sentence = ' '.join(sentence_text.split())
    sent_tokens = [clean_word(word) for word in cleaned_sentence.split()]
    
    print(f"清理后句子: '{cleaned_sentence}'")
    print(f"句子分词: {sent_tokens}")
    
    if not sent_tokens:
        print("错误: 句子分词后为空")
        return []
    
    # 获取页面所有单词及其位置
    page_words = page.get_text("words")
    
    if not page_words:
        print("错误: 页面无单词")
        return []
    
    # 增强的跨行单词合并逻辑
    cleaned_page_words = []
    i = 0
    while i < len(page_words):
        text = page_words[i][4]
        rect = fitz.Rect(page_words[i][:4])
        
        # 检查连字符情况（支持多种连字符类型）
        has_hyphen = (
            text.endswith('-') or 
            text.endswith('‐') or  # U+2010 连字符
            text.endswith('‑') or  # U+2011 不间断连字符
            text.endswith('–') or  # U+2013 短破折号
            text.endswith('—')     # U+2014 长破折号
        )
        
        # 检查下一个单词是否是当前单词的续接
        if i < len(page_words) - 1 and has_hyphen:
            next_text = page_words[i+1][4]
            
            # 合并单词（去掉连字符）
            merged_text = text.rstrip('‐‑–—') + next_text
            
            # 创建合并后的单词对象
            merged_rect = rect | fitz.Rect(page_words[i+1][:4])
            merged_word = {
                "text": merged_text,
                "cleaned": clean_word(merged_text),
                "rect": merged_rect
            }
            
            # 添加合并后的单词
            cleaned_page_words.append(merged_word)
            # 跳过下一个单词
            i += 2
            continue
        
        # 处理普通单词
        cleaned = clean_word(text)
        if cleaned:  # 跳过空单词
            cleaned_page_words.append({
                "text": text,
                "cleaned": cleaned,
                "rect": rect
            })
        i += 1
    
    # 如果页面中没有单词，直接返回
    if not cleaned_page_words:
        print("错误: 清理后页面无单词")
        return []
    
    # 打印页面单词信息
    print(f"页面单词数量: {len(cleaned_page_words)}")
    print("前10个页面单词:")
    for i, word in enumerate(cleaned_page_words[:10]):
        print(f"  {i+1}. {word['text']} ({word['cleaned']}) - {word['rect']}")
    
    # 计算平均单词宽度和高度（用于空间评分）
    avg_width = sum(r['rect'].width for r in cleaned_page_words) / len(cleaned_page_words)
    avg_height = sum(r['rect'].height for r in cleaned_page_words) / len(cleaned_page_words)
    
    # 初始化动态规划矩阵
    m = len(sent_tokens)  # 句子中的单词数
    n = len(cleaned_page_words)  # 页面中的单词数
    H = np.zeros((m+1, n+1))  # 得分矩阵
    gap_penalty = 0.5  # 跳词惩罚
    
    # 填充动态规划矩阵
    best_score = 0
    best_position = (0, 0)
    
    print(f"\n开始动态规划匹配 (句子长度: {m}, 页面单词数: {n})")
    
    for i in range(1, m+1):
        for j in range(1, n+1):
            # 计算文本相似度
            token_sim = calculate_word_similarity(sent_tokens[i-1], cleaned_page_words[j-1]['cleaned'])
            
            # 计算空间相似度（如果可能）
            spatial_score = 1.0
            if i > 1 and j > 1:
                # 获取前一个匹配的位置
                prev_rect = cleaned_page_words[j-2]['rect']
                current_rect = cleaned_page_words[j-1]['rect']
                
                # 计算距离
                dx = abs(current_rect.x0 - prev_rect.x1)
                dy = abs(current_rect.y0 - prev_rect.y0)
                
                # 计算空间得分
                spatial_score = exp(-((dx/avg_width)**2 + (dy/avg_height)**2))
            
            # 综合得分（文本相似度占80%，空间相似度占20%）
            total_score = 0.8 * token_sim + 0.2 * spatial_score
            
            # 计算各种操作得分
            match_score = H[i-1, j-1] + total_score
            delete_score = H[i-1, j] - gap_penalty
            insert_score = H[i, j-1] - gap_penalty
            
            # 选择最佳得分
            H[i, j] = max(0, match_score, delete_score, insert_score)
            
            # 更新最佳位置
            if H[i, j] > best_score:
                best_score = H[i, j]
                best_position = (i, j)
    
    print(f"最佳得分: {best_score:.2f}, 位置: {best_position}")
    
    # 如果最佳得分太低，认为没有找到匹配
    min_score = m * 0.5
    if best_score < min_score:
        print(f"未找到足够匹配的句子 (最低要求: {min_score:.2f}, 实际: {best_score:.2f})")
        return []
    
    # 回溯找到最佳匹配路径
    i, j = best_position
    path = []
    print("\n回溯路径:")

    while i > 0 and j > 0 and H[i, j] > 0:
        # 计算文本相似度用于回溯
        token_sim = calculate_word_similarity(sent_tokens[i-1], cleaned_page_words[j-1]['cleaned'])
        
        # 优先考虑匹配操作
        if H[i, j] == H[i-1, j-1] + token_sim:
            # 匹配操作
            match_word = cleaned_page_words[j-1]
            print(f"  匹配: {sent_tokens[i-1]} -> {match_word['cleaned']} (相似度: {token_sim:.2f})")
            path.append(match_word['rect'])
            i -= 1
            j -= 1
        
        # 当匹配得分不足时，考虑其他可能性
        else:
            # 检查是否可能来自上方（删除句子单词）
            if H[i, j] == H[i-1, j] - gap_penalty:
                # 删除操作（跳过句子中的单词）
                print(f"  删除句子单词: {sent_tokens[i-1]}")
                i -= 1
            
            # 检查是否可能来自左侧（插入页面单词）
            elif H[i, j] == H[i, j-1] - gap_penalty:
                # 插入操作（跳过页面中的单词）
                skip_word = cleaned_page_words[j-1]
                print(f"  跳过页面单词: {skip_word['text']} ({skip_word['cleaned']})")
                j -= 1
            
            # 当以上都不满足时，寻找最接近的路径
            else:
                # 计算三个方向的得分差异
                match_diff = abs(H[i, j] - (H[i-1, j-1] + token_sim))
                delete_diff = abs(H[i, j] - (H[i-1, j] - gap_penalty))
                insert_diff = abs(H[i, j] - (H[i, j-1] - gap_penalty))
                
                # 选择差异最小的路径
                min_diff = min(match_diff, delete_diff, insert_diff)
                
                if min_diff == match_diff:
                    # 匹配操作
                    match_word = cleaned_page_words[j-1]
                    print(f"  强制匹配: {sent_tokens[i-1]} -> {match_word['cleaned']} (相似度: {token_sim:.2f})")
                    path.append(match_word['rect'])
                    i -= 1
                    j -= 1
                elif min_diff == delete_diff:
                    # 删除操作（跳过句子中的单词）
                    print(f"  强制删除句子单词: {sent_tokens[i-1]}")
                    i -= 1
                else:
                    # 插入操作（跳过页面中的单词）
                    skip_word = cleaned_page_words[j-1]
                    print(f"  强制跳过页面单词: {skip_word['text']} ({skip_word['cleaned']})")
                    j -= 1
    
    # 反转路径以获得正确顺序
    path.reverse()
    
    # 直接返回所有匹配的单词矩形（不再分组合并）
    print(f"\n找到 {len(path)} 个匹配单词矩形:")
    for i, rect in enumerate(path):
        print(f"  {i+1}. {rect}")
    
    return path  # 直接返回单词矩形列表
