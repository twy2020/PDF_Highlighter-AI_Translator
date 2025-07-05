import threading
import re
from PyQt5 import QtCore, QtWidgets
from translator import translate_sentences, extract_and_translate_words

class TranslationWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(object, int, str)  # result, page_index, task_type
    error = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)

    def __init__(self, task_type, text, page_index):
        super().__init__()
        self.task_type = task_type
        self.text = text
        self.page_index = page_index
        self.canceled = False

    def run(self):
        try:
            self.progress.emit(f"开始处理: {self.task_type} (页面 {self.page_index + 1})")
            
            # 长文本拆分
            chunks = self._split_text(self.text)
            results = []
            
            # 多线程处理每个分块
            threads = []
            for i, chunk in enumerate(chunks):
                if self.canceled:
                    return
                    
                thread = threading.Thread(
                    target=self._process_chunk,
                    args=(chunk, i, results)
                )
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            # 按顺序合并结果
            results.sort(key=lambda x: x[0])
            merged_result = self._merge_results([r[1] for r in results])
            
            if not self.canceled:
                self.finished.emit(merged_result, self.page_index, self.task_type)
                self.progress.emit(f"完成: {self.task_type} (页面 {self.page_index + 1})")
        except Exception as e:
            self.error.emit(f"处理错误: {str(e)}")

    def _split_text(self, text):
        """智能拆分长文本"""
        # 按句子拆分
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        max_length = 1000  # 每个分块的最大字符数
        
        for sentence in sentences:
            if current_length + len(sentence) > max_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = len(sentence)
            else:
                current_chunk.append(sentence)
                current_length += len(sentence)
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks

    def _process_chunk(self, chunk, index, results):
        """处理单个文本分块"""
        try:
            if self.task_type == "sentences":
                result = translate_sentences(chunk)
            else:  # "words"
                result = extract_and_translate_words(chunk)
            
            with threading.Lock():
                results.append((index, result))
        except Exception as e:
            self.error.emit(f"分块处理错误: {str(e)}")

    def _merge_results(self, results):
        """合并多个分块的结果"""
        if self.task_type == "sentences":
            merged = []
            for r in results:
                merged.extend(r)
            return merged
        else:  # "words"
            merged = {}
            for r in results:
                merged.update(r)
            return merged

    def cancel(self):
        self.canceled = True