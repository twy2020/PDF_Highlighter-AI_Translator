from PyQt5 import QtCore, QtGui, QtWidgets

class HighlightRect(QtWidgets.QGraphicsRectItem):
    def __init__(self, rect: QtCore.QRectF, translation: str, color=None):
        super().__init__(rect)
        self.setToolTip(translation)
        self.setAcceptHoverEvents(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        
        # 设置默认颜色
        self.default_color = color if color else QtGui.QColor(255, 255, 0, 100)
        self.hover_color = QtGui.QColor(self.default_color)
        self.hover_color.setAlpha(180)  # 悬停时增加透明度
        
        self.setPen(QtGui.QPen(self.default_color.darker(120), 1))
        self.setBrush(QtGui.QBrush(self.default_color))

    def hoverEnterEvent(self, event):
        self.setBrush(QtGui.QBrush(self.hover_color))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QtGui.QBrush(self.default_color))
        super().hoverLeaveEvent(event)