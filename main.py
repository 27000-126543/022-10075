import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from src.ui.main_window import MainWindow
from src.database.db_manager import init_database


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("混凝土浇筑旁站资料整理工具")
    app.setApplicationVersion("1.0.0")
    
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    init_database()
    
    window = MainWindow()
    window.resize(1400, 900)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
