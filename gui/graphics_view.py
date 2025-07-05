import fitz
from PyQt5 import QtCore, QtGui, QtWidgets
from .highlight_rect import HighlightRect
from utils import clean_text

class GraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)
        self.rubber = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self.origin = QtCore.QPoint()
        self.zoom = 1.0
        self.current_page = None  # 存储当前页面的 fitz.Page 对象
        self.current_page_index = -1  # 存储当前页面索引

    def set_page(self, pixmap, page, page_index, zoom):
        """设置当前页面"""
        # 清除场景
        self.scene.clear()
        self.zoom = zoom
        self.current_page = page  # 存储 fitz.Page 对象
        self.current_page_index = page_index  # 存储页面索引
        self.scene.addPixmap(pixmap)
        self.setSceneRect(QtCore.QRectF(pixmap.rect()))

    def mousePressEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            self.origin = ev.pos()
            self.rubber.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
            self.rubber.show()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self.rubber.isVisible():
            self.rubber.setGeometry(QtCore.QRect(self.origin, ev.pos()).normalized())
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton and self.rubber.isVisible():
            self.rubber.hide()
            rect = self.rubber.geometry()
            p1 = self.mapToScene(rect.topLeft())
            p2 = self.mapToScene(rect.bottomRight())
            
            if self.current_page is not None:
                # 获取精确的选择矩形（考虑缩放）
                pdf_r = fitz.Rect(
                    min(p1.x(), p2.x()) / self.zoom,
                    min(p1.y(), p2.y()) / self.zoom,
                    max(p1.x(), p2.x()) / self.zoom,
                    max(p1.y(), p2.y()) / self.zoom
                )
                
                # 获取文本并清理
                text = self.current_page.get_textbox(pdf_r)
                cleaned_text = clean_text(text)
                
                # 修复：使用 self.parent_window 而不是 self.parent
                self.parent_window.update_selection_display(cleaned_text)
        super().mouseReleaseEvent(ev)
    
    def wheelEvent(self, ev):
        mods, d = QtWidgets.QApplication.keyboardModifiers(), ev.angleDelta().y()
        if mods == QtCore.Qt.ControlModifier:
            self.parent_window.zoom *= 1.25 if d > 0 else 0.8
            self.parent_window.load_page()
        elif mods == QtCore.Qt.AltModifier:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d)
        else:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d)