from PyQt5 import QtWidgets
from utils import export_to_csv, export_sentences_to_csv

class ExportManager:
    @staticmethod
    def export_words(words, parent, all_pages=False):
        if not words:
            QtWidgets.QMessageBox.information(parent, "Info", 
                "无单词可导出" if all_pages else "当前页无单词")
            return False
        
        title = "导出全部单词" if all_pages else "导出当前页单词"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(parent, title, "", "CSV Files (*.csv)")
        if not path:
            return False
        
        success, count = export_to_csv(words, path, parent)
        if success:
            QtWidgets.QMessageBox.information(parent, "完成", f"已导出 {count} 个单词到 {path}")
        return success

    @staticmethod
    def export_sentences(sentences, parent, all_pages=False):
        if not sentences:
            QtWidgets.QMessageBox.information(parent, "Info", 
                "无句子可导出" if all_pages else "当前页无句子")
            return False
        
        title = "导出全部句子" if all_pages else "导出当前页句子"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(parent, title, "", "CSV Files (*.csv)")
        if not path:
            return False
        
        # 准备导出数据
        export_data = [{'original': s['original'], 'translation': s['translation']} for s in sentences]
        success, count = export_sentences_to_csv(export_data, path, parent)
        if success:
            QtWidgets.QMessageBox.information(parent, "完成", f"已导出 {count} 个句子到 {path}")
        return success