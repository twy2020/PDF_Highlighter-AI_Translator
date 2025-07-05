import fitz
from PyQt5 import QtCore, QtGui, QtWidgets
from .highlight_rect import HighlightRect
from translator import find_word_in_page, find_sentence_in_page
import uuid

class HighlightManager:
    def __init__(self, doc, view):
        self.doc = doc
        self.view = view
        self.zoom = 1.0
        
        # 新的数据结构：按页面存储高亮信息
        self.page_highlights = {}  # 格式: {page_index: {'words': {}, 'sentences': {}}}

        # 新增：页面翻译状态
        self.page_translation_tasks = {}  # 格式: {page_index: {'active': int, 'completed': int}}
        
        # 存储翻译数据
        self.translations = {
            'words': {},      # {page_index: {word: translation}}
            'sentences': []   # [{'id': str, 'original': str, 'translation': str, 'page': int}]
        }

        self.first_occurrence_positions = {}
        
        # 默认颜色
        self.default_word_color = QtGui.QColor(255, 255, 0, 100)  # 黄色
        self.default_sentence_color = QtGui.QColor(173, 216, 230, 100)  # 淡蓝色

    def set_zoom(self, zoom):
        """设置缩放比例"""
        self.zoom = zoom

    def add_word_translation(self, word, translation, page_index):
        """添加单词翻译"""
        if page_index not in self.translations['words']:
            self.translations['words'][page_index] = {}
        self.translations['words'][page_index][word] = translation

    def add_sentences(self, sentences, page_index):
        """添加一组句子翻译"""
        # 增加句子组ID
        self.current_sentence_group = getattr(self, 'current_sentence_group', 0) + 1
        
        for sent in sentences:
            sent['group_id'] = self.current_sentence_group
            sent['page'] = page_index
            if 'id' not in sent:
                sent['id'] = str(uuid.uuid4())
            self.translations['sentences'].append(sent)

    def get_current_page_sentences(self, page_index):
        """获取当前页的句子"""
        return [sent for sent in self.translations['sentences'] if sent['page'] == page_index]

    def find_word_rects(self, page, word):
        """查找单词在页面中的位置"""
        # 首先尝试标准搜索
        rects = page.search_for(word)
        
        # 如果找不到，尝试更智能的搜索
        if not rects:
            rects = find_word_in_page(page, word)
        
        # 如果仍然找不到，尝试模糊匹配
        if not rects:
            base_word = word
            if word.endswith("'s"):
                base_word = word[:-2]
            elif word.endswith("s") and len(word) > 1:
                base_word = word[:-1]
            elif word.endswith("ed") and len(word) > 2:
                base_word = word[:-2]
            elif word.endswith("ing") and len(word) > 3:
                base_word = word[:-3]
            
            if base_word != word:
                rects = page.search_for(base_word)
                if not rects:
                    rects = find_word_in_page(page, base_word)
        
        return rects

    def parse_color(self, color_str, for_word=True):
        """解析颜色字符串，根据上下文返回单词或句子默认颜色"""
        try:
            if color_str.startswith("#"):
                # HEX格式 #RRGGBB 或 #RRGGBBAA
                hex_str = color_str[1:]
                if len(hex_str) == 6:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    return QtGui.QColor(r, g, b, 100)
                elif len(hex_str) == 8:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    a = int(hex_str[6:8], 16)
                    return QtGui.QColor(r, g, b, a)
            elif color_str.startswith("rgb("):
                # RGB格式 rgb(r,g,b)
                values = color_str[4:-1].split(",")
                r = int(values[0].strip())
                g = int(values[1].strip())
                b = int(values[2].strip())
                return QtGui.QColor(r, g, b, 100)
            elif color_str.startswith("rgba("):
                # RGBA格式 rgba(r,g,b,a)
                values = color_str[5:-1].split(",")
                r = int(values[0].strip())
                g = int(values[1].strip())
                b = int(values[2].strip())
                a = int(float(values[3].strip()) * 255)
                return QtGui.QColor(r, g, b, a)
        except Exception as e:
            print(f"颜色解析错误: {str(e)}")
        
        # 根据上下文返回默认颜色
        return self.default_word_color if for_word else self.default_sentence_color

    def highlight_word(self, word, page_index, color_str=None):
        """高亮单词 - 改进版，处理被拆分的单词，支持自定义颜色"""
        # 确保页面数据结构存在
        if page_index not in self.page_highlights:
            self.page_highlights[page_index] = {'words': {}, 'sentences': {}}
        
        # 获取页面高亮信息
        page_data = self.page_highlights[page_index]
        
        # 检查是否已高亮 - 如果已高亮但颜色不同，也更新
        if word in page_data['words']:
            # 如果已高亮但颜色不同，先取消高亮再重新高亮
            if page_data['words'][word].get('highlighted', False):
                current_color = page_data['words'][word]['color']
                new_color = self.parse_color(color_str, for_word=True) if color_str else self.default_word_color
                
                # 如果颜色不同，取消高亮以便重新高亮
                if current_color != new_color:
                    self.unhighlight_word(word, page_index)
                else:
                    # 颜色相同且已高亮，无需操作
                    return False
        
        # 解析颜色
        color = self.parse_color(color_str, for_word=True) if color_str else self.default_word_color
        
        # 获取翻译
        translation = self.translations['words'].get(page_index, {}).get(word, "")
        
        # 在页面中查找单词位置
        page = self.doc[page_index]
        rects = self.find_word_rects(page, word)
        
        if not rects:
            print(f"未找到单词: {word}")
            return False
        
        # 存储高亮信息
        page_data['words'][word] = {
            'rects': rects,
            'color': color,
            'translation': translation,
            'highlighted': True
        }
        
        # 如果当前是活动页面，立即绘制
        if hasattr(self.view, 'current_page_index') and self.view.current_page_index == page_index:
            # 直接绘制这个单词的高亮
            self.draw_word_highlight(word, page_index)
        
        return True

    def draw_word_highlight(self, word, page_index):
        """绘制单词高亮"""
        if page_index not in self.page_highlights:
            return
        page_data = self.page_highlights[page_index]
        if word not in page_data['words']:
            return
        
        word_info = page_data['words'][word]
        if not word_info['highlighted']:
            return
        
        # 移除旧的高亮项（如果有）
        if 'items' in word_info:
            for item in word_info['items']:
                try:
                    if item and hasattr(item, 'scene') and item.scene():
                        self.view.scene.removeItem(item)
                except RuntimeError:
                    pass
        
        # 创建新的高亮项
        items = []
        for rect in word_info['rects']:
            # 应用当前缩放比例
            r = rect * self.zoom
            rectF = QtCore.QRectF(r.x0, r.y0, r.width, r.height)
            try:
                hl = HighlightRect(rectF, word_info['translation'], word_info['color'])
                self.view.scene.addItem(hl)
                items.append(hl)
            except Exception as e:
                print(f"创建高亮项失败: {str(e)}")
        
        # 存储高亮项引用
        word_info['items'] = items

    def draw_sentence_highlight(self, sent_id, page_index):
        """绘制句子高亮 - 精确绘制每个单词矩形"""
        if page_index not in self.page_highlights:
            return
        
        page_data = self.page_highlights[page_index]
        if sent_id not in page_data['sentences']:
            return
        
        sent_info = page_data['sentences'][sent_id]
        if not sent_info['highlighted']:
            return
        
        # 彻底移除所有旧的高亮项
        if 'items' in sent_info:
            for hl in sent_info['items']:
                try:
                    if hl and hasattr(hl, 'scene') and hl.scene():
                        self.view.scene.removeItem(hl)
                except RuntimeError:
                    # 忽略已删除项
                    pass
            # 清空引用
            sent_info['items'] = []
        
        # 创建新的高亮项 - 为每个单词矩形创建独立高亮
        items = []
        
        # 计算首单词颜色（加深50%）
        base_color = sent_info['color']
        first_word_color = base_color.darker(180)  # 加深50%
        
        for idx, rect in enumerate(sent_info['rects']):
            # 应用当前缩放比例
            scaled_rect = fitz.Rect(
                rect.x0 * self.zoom,
                rect.y0 * self.zoom,
                rect.x1 * self.zoom,
                rect.y1 * self.zoom
            )
            
            # 创建QRectF对象
            rectF = QtCore.QRectF(
                scaled_rect.x0, scaled_rect.y0,
                scaled_rect.width, scaled_rect.height
            )
            
            # 跳过代表整个句子的大矩形
            page_width = self.doc[page_index].rect.width * self.zoom
            if rectF.width() > page_width * 0.2 or rectF.height() > page_width * 0.1:
                print(f"跳过整个句子的大矩形: {rectF}")
                continue
            
            try:
                # 如果是首单词，使用深色
                color = first_word_color if idx == 0 else base_color
                
                # 创建高亮项
                hl = HighlightRect(rectF, sent_info['translation'], color)
                self.view.scene.addItem(hl)
                items.append(hl)
                
                # 调试信息
                print(f"添加单词高亮: {rectF} (原始: {rect})")
            except Exception as e:
                print(f"创建单词高亮失败: {str(e)}")
        
        # 存储高亮项引用
        sent_info['items'] = items

    def draw_page_highlights(self, page_index):
        """绘制指定页面的所有高亮"""
        if page_index not in self.page_highlights:
            return
        
        page_data = self.page_highlights[page_index]
        
        # 绘制单词高亮
        for word in list(page_data['words'].keys()):
            if page_data['words'][word]['highlighted']:
                self.draw_word_highlight(word, page_index)
        
        # 绘制句子高亮
        for sent_id in list(page_data['sentences'].keys()):
            if page_data['sentences'][sent_id]['highlighted']:
                self.draw_sentence_highlight(sent_id, page_index)

    def unhighlight_word(self, word, page_index):
        """取消单词高亮"""
        if page_index not in self.page_highlights:
            return False
        page_data = self.page_highlights[page_index]
        if word not in page_data['words']:
            return False
        
        word_info = page_data['words'][word]
        
        # 移除高亮项
        if 'items' in word_info:
            for hl in word_info['items']:
                try:
                    if hl and hasattr(hl, 'scene') and hl.scene():
                        self.view.scene.removeItem(hl)
                except RuntimeError:
                    pass
            word_info['items'] = []
        
        # 更新状态
        word_info['highlighted'] = False
        return True

    def clear_page_word_highlights(self, page_index):
        """清除指定页面所有单词高亮"""
        if page_index not in self.page_highlights:
            return
        
        words = list(self.page_highlights[page_index]['words'].keys())
        for word in words:
            self.unhighlight_word(word, page_index)

    def is_word_highlighted(self, word, page_index):
        """检查单词是否已高亮"""
        return (page_index in self.page_highlights and 
                word in self.page_highlights[page_index]['words'] and 
                self.page_highlights[page_index]['words'][word]['highlighted'])

    def highlight_sentence(self, sent_id, page_index, color_str=None):
        """高亮句子 - 支持自定义颜色"""
        print(f"\n===== 开始高亮句子 (ID: {sent_id}, 页面: {page_index}) =====")
        
        # 确保页面数据结构存在
        if page_index not in self.page_highlights:
            self.page_highlights[page_index] = {'words': {}, 'sentences': {}}
        
        # 获取页面高亮信息
        page_data = self.page_highlights[page_index]
        
        # 检查是否已高亮 - 如果已高亮但颜色不同，也更新
        if sent_id in page_data['sentences']:
            # 如果已高亮但颜色不同，先取消高亮再重新高亮
            if page_data['sentences'][sent_id].get('highlighted', False):
                current_color = page_data['sentences'][sent_id]['color']
                new_color = self.parse_color(color_str, for_word=False) if color_str else self.default_sentence_color
                
                # 如果颜色不同，取消高亮以便重新高亮
                if current_color != new_color:
                    self.unhighlight_sentence(sent_id)
                else:
                    # 颜色相同且已高亮，无需操作
                    print("句子已高亮且颜色相同，跳过")
                    return False
        
        # 查找句子
        sentence = None
        for sent in self.translations['sentences']:
            if sent.get('id') == sent_id:
                sentence = sent
                break
        
        if not sentence:
            print(f"错误: 未找到句子 {sent_id}")
            return False
        
        print(f"句子原文: '{sentence['original']}'")
        print(f"句子翻译: '{sentence['translation']}'")
        
        # 在页面中查找句子
        page = self.doc[page_index]
        word_rects = find_sentence_in_page(page, sentence['original'])
        
        if not word_rects:
            print(f"错误: 未在页面中找到句子: {sentence['original']}")
            return False
        
        print(f"找到 {len(word_rects)} 个匹配单词矩形")
        
        # 直接使用单词矩形，不进行分组合并
        # 解析颜色
        color = self.parse_color(color_str, for_word=False) if color_str else self.default_sentence_color
        
        # 存储高亮信息
        page_data['sentences'][sent_id] = {
            'rects': word_rects,  # 直接存储单词矩形
            'color': color,
            'translation': sentence['translation'],
            'highlighted': True
        }
        
        # 如果当前是活动页面，立即绘制
        if hasattr(self.view, 'current_page_index') and self.view.current_page_index == page_index:
            self.draw_sentence_highlight(sent_id, page_index)
        
        return True

    def unhighlight_sentence(self, sent_id):
        """取消句子高亮"""
        # 查找句子所在的页面
        page_index = None
        for sent in self.translations['sentences']:
            if sent.get('id') == sent_id:
                page_index = sent.get('page')
                break
        
        if page_index is None or page_index not in self.page_highlights:
            return False
        
        page_data = self.page_highlights[page_index]
        if sent_id not in page_data['sentences']:
            return False
        
        sent_info = page_data['sentences'][sent_id]
        
        # 移除高亮项
        if 'items' in sent_info:
            for hl in sent_info['items']:
                try:
                    if hl and hasattr(hl, 'scene') and hl.scene():
                        self.view.scene.removeItem(hl)
                except RuntimeError:
                    pass
            sent_info['items'] = []
        
        # 更新状态
        sent_info['highlighted'] = False
        
        # 如果当前是活动页面，立即重绘
        if hasattr(self.view, 'current_page_index') and self.view.current_page_index == page_index:
            self.draw_page_highlights(page_index)
        
        return True

    def is_sentence_highlighted(self, sent_id):
        """检查句子是否已高亮"""
        # 查找句子所在的页面
        page_index = None
        for sent in self.translations['sentences']:
            if sent.get('id') == sent_id:
                page_index = sent.get('page')
                break
        
        return (page_index is not None and 
                page_index in self.page_highlights and 
                sent_id in self.page_highlights[page_index]['sentences'] and 
                self.page_highlights[page_index]['sentences'][sent_id]['highlighted'])

    def clear_page_sentence_highlights(self, page_index):
        """清除指定页面所有句子高亮"""
        if page_index not in self.page_highlights:
            return
        
        sent_ids = list(self.page_highlights[page_index]['sentences'].keys())
        for sent_id in sent_ids:
            self.unhighlight_sentence(sent_id)

    def get_word_highlight_info(self, page_index):
        """获取单词高亮信息用于表格更新"""
        highlighted_words = []
        if page_index in self.page_highlights:
            for word, info in self.page_highlights[page_index]['words'].items():
                if info['highlighted']:
                    highlighted_words.append(word)
        
        word_map = self.translations['words'].get(page_index, {})
        return word_map, highlighted_words

    def get_sentence_highlight_info(self, page_index):
        """获取句子高亮信息用于表格更新"""
        highlighted_ids = []
        if page_index in self.page_highlights:
            for sent_id, info in self.page_highlights[page_index]['sentences'].items():
                if info['highlighted']:
                    highlighted_ids.append(sent_id)
        
        sentences = self.get_current_page_sentences(page_index)
        return sentences, highlighted_ids
    
    def remove_sentence(self, sent_id):
        """从翻译数据中移除指定ID的句子，并取消其高亮"""
        # 首先取消高亮（如果已高亮）
        self.unhighlight_sentence(sent_id)
        
        # 从翻译数据中移除句子
        for i, sent in enumerate(self.translations['sentences']):
            if sent.get('id') == sent_id:
                self.translations['sentences'].pop(i)
                break

    def remove_word(self, word, page_index):
        """从翻译数据中移除指定单词，并取消其高亮"""
        # 首先取消高亮（如果已高亮）
        self.unhighlight_word(word, page_index)
        
        # 从翻译数据中移除单词
        if page_index in self.translations['words']:
            if word in self.translations['words'][page_index]:
                del self.translations['words'][page_index][word]
                
                # 如果该页没有其他单词，移除整个页面
                if not self.translations['words'][page_index]:
                    del self.translations['words'][page_index]

    def start_translation_task(self, page_index):
        """开始一个新的翻译任务"""
        if page_index not in self.page_translation_tasks:
            self.page_translation_tasks[page_index] = {'active': 0, 'completed': 0}
        self.page_translation_tasks[page_index]['active'] += 1
        
    def complete_translation_task(self, page_index):
        """完成一个翻译任务"""
        if page_index in self.page_translation_tasks:
            self.page_translation_tasks[page_index]['active'] = max(0, self.page_translation_tasks[page_index]['active'] - 1)
            self.page_translation_tasks[page_index]['completed'] += 1
            
    def clear_page_status(self, page_index):
        """清除页面的翻译状态"""
        if page_index in self.page_translation_tasks:
            self.page_translation_tasks[page_index]['completed'] = 0
            
    def get_page_translation_status(self, page_index):
        """获取页面的翻译状态"""
        if page_index not in self.page_translation_tasks:
            return 0
            
        tasks = self.page_translation_tasks[page_index]
        if tasks['active'] > 0:
            return 1  # 有活动任务
        elif tasks['completed'] > 0:
            return 2  # 有已完成任务
        return 0  # 无状态
    def group_word_rects(self, rects):
        """按行分组连续的矩形 - 精确版"""
        if not rects:
            return []
        
        # 按y坐标分组（行） - 使用更精确的分组方法
        rects.sort(key=lambda r: (r.y0, r.x0))  # 先按y后按x排序
        lines = []
        current_line = []
        
        for i, rect in enumerate(rects):
            if not current_line:
                current_line.append(rect)
                continue
            
            # 获取当前行的y0范围
            min_y = min(r.y0 for r in current_line)
            max_y = max(r.y1 for r in current_line)
            line_height = max_y - min_y
            
            # 检查是否属于同一行：y0在行高范围内
            last_rect = current_line[-1]
            y_diff = abs(rect.y0 - last_rect.y0)
            
            # 更严格的行分组条件
            if y_diff < line_height * 0.2:  # 20%行高阈值
                current_line.append(rect)
            else:
                # 新行开始
                lines.append(current_line)
                current_line = [rect]
        
        # 添加最后一行
        if current_line:
            lines.append(current_line)
        
        # 对每行内的矩形按x坐标排序
        grouped_rects = []
        for line in lines:
            line.sort(key=lambda r: r.x0)
            
            # 合并连续矩形
            current_group = []
            for rect in line:
                if not current_group:
                    current_group.append(rect)
                    continue
                
                # 检查是否与前一个矩形连续
                prev_rect = current_group[-1]
                gap = rect.x0 - prev_rect.x1
                
                # 如果间距小于平均宽度的0.8倍，视为连续
                avg_width = (prev_rect.width + rect.width) / 2
                if gap < avg_width * 0.8:
                    current_group.append(rect)
                else:
                    # 保存当前组并开始新组
                    if current_group:
                        grouped_rects.append(current_group)
                    current_group = [rect]
            
            # 添加最后一个组
            if current_group:
                grouped_rects.append(current_group)
        
        # 创建合并后的矩形
        merged_rects = []
        for group in grouped_rects:
            if len(group) == 1:
                merged_rects.append(group[0])
            else:
                # 创建覆盖整个组的矩形 - 精确合并
                x0 = min(r.x0 for r in group)
                y0 = min(r.y0 for r in group)
                x1 = max(r.x1 for r in group)
                y1 = max(r.y1 for r in group)
                merged_rect = fitz.Rect(x0, y0, x1, y1)
                merged_rects.append(merged_rect)
        
        return merged_rects