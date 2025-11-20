# 파일 이름: app_ui.py

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QFrame,
                             QMessageBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QHBoxLayout, QStyle, QSlider, QGridLayout,
                             QCheckBox)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPalette

# --- 1. 로직 파일 임포트 ---
import app_logic 

# --- Matplotlib 임포트 ---
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True

    # --- [수정] Matplotlib 한글 폰트 설정 ---
    try:
        # 'Malgun Gothic'은 Windows의 기본 한글 폰트입니다.
        plt.rcParams['font.family'] = 'Malgun Gothic'
        # 폰트가 깨질 때 대비, 유니코드 마이너스 부호 설정
        plt.rcParams['axes.unicode_minus'] = False 
        print("Matplotlib 한글 폰트(맑은 고딕) 설정 완료.")
    except Exception as e:
        print(f"⚠️ Matplotlib 한글 폰트 설정 실패: {e}. (그래프 한글이 깨질 수 있습니다)")
    # --- [수정 끝] ---

except ImportError:
    print("⚠️ Matplotlib 라이브러리를 찾을 수 없습니다. 그래프 기능이 비활성화됩니다.")
    print("   터미널/명령 프롬프트에서 `pip install matplotlib`를 실행하세요.")
    MATPLOTLIB_AVAILABLE = False


# --- 스타일시트 로더 함수 (변경 없음) ---
def load_stylesheet(file_name):
    """지정된 QSS 파일을 읽어와서 텍스트로 반환"""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️ 스타일시트 파일 '{file_name}'을(를) 찾을 수 없습니다.")
        return "" 
    except Exception as e:
        print(f"⚠️ 스타일시트 로드 오류: {e}")
        return ""


# --- 시작 화면 (UI 클래스) (변경 없음) ---
class StartPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        main_layout = QVBoxLayout(self)
        main_layout.addStretch(1) 
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(20)
        title = QLabel("파일 유틸리티")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("수행할 작업을 선택하세요.")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        btn_dup = self.create_function_button(
            controller,
            index=1,
            icon=QApplication.style().standardIcon(QStyle.SP_DialogYesButton),
            title="중복 파일 검사",
            description="폴더 내의 100% 동일한 파일을 찾아 정리합니다."
        )
        btn_sim = self.create_function_button(
            controller,
            index=2,
            icon=QApplication.style().standardIcon(QStyle.SP_FileIcon),
            title="유사 이미지 스캐너",
            description="폴더 내의 비슷하지만 다른 이미지들을 찾아냅니다."
        )
        btn_iqa = self.create_function_button(
            controller,
            index=3, # 새로운 페이지 인덱스 (3번)
            icon=QApplication.style().standardIcon(QStyle.SP_ComputerIcon),
            title="이미지 품질 검사 (IQA)",
            description="AI(CLIP/BRISQUE)를 이용해 사진의 미적/기술적 품질 점수를 측정합니다."
        )
        button_layout.addStretch(1)
        button_layout.addWidget(btn_dup, 2)
        button_layout.addWidget(btn_sim, 2)
        button_layout.addWidget(btn_iqa, 2)
        button_layout.addStretch(1) 
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addSpacing(30)
        main_layout.addLayout(button_layout)
        main_layout.addStretch(1) 
    def create_function_button(self, controller, index, icon, title, description):
        button = QPushButton()
        button.setObjectName("FunctionButton")
        button.setMinimumWidth(300) 
        layout = QVBoxLayout(button)
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
        icon_label.setAlignment(Qt.AlignLeft)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FFFFFF;")
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #AAAAAA; font-size: 9pt;")
        desc_label.setWordWrap(True)
        layout.addWidget(icon_label)
        layout.addSpacing(10)
        layout.addStretch(1)
        layout.addWidget(title_label)
        layout.addStretch(1)
        layout.addWidget(desc_label)
        button.clicked.connect(lambda: controller.setCurrentIndex(index))
        return button

# --- Matplotlib 캔버스 위젯 (UI 클래스) (변경 없음) ---
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # [참고] 여기서 'dark_background' 대신 plt.rcParams로 폰트를 설정했습니다.
        # plt.style.use('dark_background') # 스타일시트가 이미 어두우므로 필수 아님
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#3A3A3A')
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

# --- 통계 패널 위젯 (UI 클래스) (변경 없음) ---
class StatisticsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #3A3A3A; border-radius: 4px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.stats_label = QLabel("스캔할 폴더를 드래그하세요.")
        self.stats_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("padding: 10px; font-size: 10pt; background-color: #2E2E2E; border-radius: 4px;")
        self.stats_label.setMinimumHeight(120)
        if MATPLOTLIB_AVAILABLE:
            self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
            layout.addWidget(self.stats_label)
            layout.addWidget(self.canvas)
        else:
            self.stats_label.setText("Matplotlib 라이브러리가 없어 그래프를 표시할 수 없습니다.\n`pip install matplotlib`를 실행하세요.")
            layout.addWidget(self.stats_label)
    
    def update_stats(self, total_files, total_size, total_duplicates, total_dup_space, space_by_category):
        valid_categories = {k: v for k, v in space_by_category.items() if v > 0}
        text = f"""
        <b>📊 스캔 통계</b><br>
        &nbsp; • 총 스캔 파일: {total_files} 개<br>
        &nbsp; • 총 스캔 용량: {app_logic.format_bytes(total_size)}<br> 
        <hr style='border: 1px solid #444;'>
        <b>💾 중복 파일 현황</b><br>
        &nbsp; • 중복 파일 수: <b>{total_duplicates} 개</b> (총 {len(valid_categories)}개 유형)<br>
        &nbsp; • 낭비되는 용량: <font color='#FF6347' size='+1'><b>{app_logic.format_bytes(total_dup_space)}</b></font>
        """
        self.stats_label.setText(text)
        if not MATPLOTLIB_AVAILABLE: return
        self.canvas.axes.clear()
        
        if not valid_categories or total_dup_space == 0:
            self.canvas.axes.text(0.5, 0.5, "중복 파일 없음", 
                                  horizontalalignment='center', verticalalignment='center', 
                                  fontsize=12, color='gray')
            self.canvas.axes.set_facecolor('#3A3A3A')
            self.canvas.draw()
            return
            
        labels = valid_categories.keys()
        sizes = valid_categories.values()
        
        def autopct_format(pct):
            if pct < 5: return ''
            return f'{pct:.1f}%'
            
        # [참고] 여기서 사용되는 폰트는 plt.rcParams에 의해 '맑은 고딕'으로 자동 설정됩니다.
        wedges, texts, autotexts = self.canvas.axes.pie(
            sizes, labels=labels, autopct=autopct_format,
            startangle=90, pctdistance=0.85, labeldistance=1.1,
            textprops={'color': '#E0E0E0', 'fontsize': 9}
        )
        centre_circle = plt.Circle((0,0), 0.70, fc='#3A3A3A')
        self.canvas.axes.add_artist(centre_circle)
        
        # [참고] 이 텍스트가 한글("총 낭비 용량")이므로 폰트 설정이 필요했습니다.
        self.canvas.axes.text(0, 0, f"총 낭비 용량\n{app_logic.format_bytes(total_dup_space)}", 
                              ha='center', va='center', color='#FF6347', fontsize=12, fontweight='bold')
        
        self.canvas.axes.axis('equal')
        self.canvas.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    def reset(self):
        self.stats_label.setText("스캔할 폴더를 드래그하세요.")
        if MATPLOTLIB_AVAILABLE:
            self.canvas.axes.clear()
            self.canvas.axes.set_facecolor('#3A3A3A')
            self.canvas.draw()

# --- 중복 파일 검사 화면 (UI 클래스) ---
class DuplicateCheckPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setAcceptDrops(True)
        self.current_stats = {}
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        left_layout = QVBoxLayout()
        self.info_label = QLabel("\n\n결과를 표시할 폴더를\n이곳으로 드래그 앤 드롭하세요.\n\n")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setMinimumHeight(150)
        self.result_table = QTableWidget()
        self.result_table.setObjectName("ResultTable")
        
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["선택", "파일 경로", "용량"])

        # --- [수정] '선택' 열 너비 고정 ---
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.result_table.setColumnWidth(0, 50) # 50px로 너비 고정
        # --- [수정 끝] ---
        
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        
        left_layout.addWidget(self.info_label, 1)
        left_layout.addWidget(self.result_table, 3)
        
        right_layout = QVBoxLayout()
        self.stats_widget = StatisticsWidget(self)
        self.batch_delete_btn = QPushButton("선택한 파일 삭제")
        self.batch_delete_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_TrashIcon))
        self.batch_delete_btn.setStyleSheet("background-color: #7A3A3A;")
        self.batch_delete_btn.clicked.connect(self.handle_batch_delete)
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignRight)
        reset_btn = QPushButton("다시 하기")
        reset_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        reset_btn.setMinimumWidth(120)
        reset_btn.setMinimumHeight(35)
        reset_btn.clicked.connect(self.reset_page)
        back_btn = QPushButton("뒤로 가기")
        back_btn.setMinimumWidth(120)
        back_btn.setMinimumHeight(35)
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))
        button_layout.addStretch(1)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(back_btn)
        
        right_layout.addWidget(self.stats_widget, 1)
        right_layout.addWidget(self.batch_delete_btn)
        right_layout.addLayout(button_layout)

        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)

    def reset_page(self):
        # (변경 없음)
        self.info_label.setText("\n\n결과를 표시할 폴더를\n이곳으로 드래그 앤 드롭하세요.\n\n")
        self.info_label.setStyleSheet("")
        self.result_table.setRowCount(0)
        self.stats_widget.reset()
        self.current_stats = {}

    def dragEnterEvent(self, event):
        # (변경 없음)
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
            self.info_label.setStyleSheet("border-color: #0078D7; color: #E0E0E0;")
        else: event.ignore()

    def dragLeaveEvent(self, event): self.reset_page()

    def dropEvent(self, event):
        # (변경 없음)
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return
        folder_path = files[0]
        if os.path.isdir(folder_path):
            self.info_label.setText(f"'{os.path.basename(folder_path)}' 폴더 검사 중...")
            QApplication.processEvents()
            duplicates, total_files, total_size = app_logic.find_duplicate_files(folder_path)
            self.process_statistics(duplicates, total_files, total_size)
            self.populate_table(duplicates)
            if not duplicates:
                self.info_label.setText("✅ 검사 완료: 중복된 파일이 없습니다.")
            else:
                self.info_label.setText(f"검색 완료. 중복된 파일 목록은 아래와 같습니다.")
        else:
            self.info_label.setText("⚠️ 폴더가 아닙니다. 폴더를 드래그 앤 드롭해주세요.")
            self.stats_widget.reset()
            self.current_stats = {}

    def process_statistics(self, duplicates, total_files, total_size):
        # (변경 없음)
        total_duplicate_files = 0
        total_duplicate_space = 0
        from collections import defaultdict
        space_by_category = defaultdict(int)
        if duplicates:
            for paths in duplicates.values():
                if not paths: continue
                try:
                    file_size = os.path.getsize(paths[0])
                    category = app_logic.get_file_category(paths[0])
                except FileNotFoundError:
                    continue
                num_duplicates_in_group = len(paths) - 1
                space_taken_by_duplicates = file_size * num_duplicates_in_group
                total_duplicate_files += num_duplicates_in_group
                total_duplicate_space += space_taken_by_duplicates
                space_by_category[category] += space_taken_by_duplicates
        self.current_stats = {
            'total_files': total_files,
            'total_size': total_size,
            'total_duplicates': total_duplicate_files,
            'total_dup_space': total_duplicate_space,
            'space_by_category': dict(space_by_category)
        }
        self.stats_widget.update_stats(**self.current_stats)

    def populate_table(self, duplicates):
        # (변경 없음)
        self.result_table.setRowCount(0)
        for file_hash, paths in duplicates.items():
            md5_part, sha_part = file_hash.split("_")
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            header_item = QTableWidgetItem(f"🔑 동일 파일 그룹 (MD5: {md5_part[:10]}...)")
            header_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            header_item.setBackground(QColor("#4A4A4A"))
            self.result_table.setSpan(row_position, 0, 1, 3) 
            self.result_table.setItem(row_position, 0, header_item)
            for path in paths:
                try:
                    file_size = os.path.getsize(path)
                    file_category = app_logic.get_file_category(path)
                except FileNotFoundError:
                    continue 
                row_position = self.result_table.rowCount()
                self.result_table.insertRow(row_position)
                checkbox_widget = QWidget()
                chk_layout = QHBoxLayout(checkbox_widget)
                chk_box = QCheckBox()
                chk_layout.addWidget(chk_box)
                chk_layout.setAlignment(Qt.AlignCenter)
                chk_layout.setContentsMargins(0,0,0,0)
                checkbox_widget.setLayout(chk_layout)
                chk_box.setProperty("file_path", path)
                chk_box.setProperty("file_size", file_size)
                chk_box.setProperty("file_category", file_category)
                chk_box.setProperty("table_row", row_position)
                self.result_table.setCellWidget(row_position, 0, checkbox_widget)
                path_item = QTableWidgetItem(path)
                self.result_table.setItem(row_position, 1, path_item)
                size_item = QTableWidgetItem(app_logic.format_bytes(file_size))
                self.result_table.setItem(row_position, 2, size_item)

    def handle_batch_delete(self):
        # (변경 없음)
        files_to_delete = []
        for row in range(self.result_table.rowCount()):
            cell_widget = self.result_table.cellWidget(row, 0)
            if cell_widget:
                chk_box = cell_widget.findChild(QCheckBox)
                if chk_box and chk_box.isChecked():
                    files_to_delete.append((
                        chk_box.property("table_row"),
                        chk_box.property("file_path"),
                        chk_box.property("file_size"),
                        chk_box.property("file_category")
                    ))
        if not files_to_delete:
            QMessageBox.information(self, "선택 없음", "삭제할 파일을 하나 이상 선택하세요.")
            return
        total_size_to_delete = sum(item[2] for item in files_to_delete)
        reply = QMessageBox.question(self, '일괄 삭제 확인',
                                     f"정말로 <b>{len(files_to_delete)}개</b>의 파일을 영구적으로 삭제하시겠습니까?<br><br>"
                                     f"<b><font color='#FF6347'>총 확보 용량: {app_logic.format_bytes(total_size_to_delete)}</font></b><br><br>"
                                     f"이 작업은 되돌릴 수 없습니다.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return
        deleted_count = 0
        space_saved = 0
        for row, path, size, category in sorted(files_to_delete, key=lambda x: x[0], reverse=True):
            try:
                os.remove(path)
                self.result_table.removeRow(row)
                self.current_stats['total_duplicates'] -= 1
                self.current_stats['total_dup_space'] -= size
                if category in self.current_stats['space_by_category']:
                    self.current_stats['space_by_category'][category] -= size
                deleted_count += 1
                space_saved += size
            except Exception as e:
                print(f"파일 삭제 오류 ({path}): {e}")
        if deleted_count > 0:
            print("그래프 업데이트 중...")
            self.stats_widget.update_stats(**self.current_stats)
            QMessageBox.information(self, "삭제 완료",
                                    f"총 {deleted_count}개의 파일을 삭제했습니다.\n"
                                    f"확보된 용량: {app_logic.format_bytes(space_saved)}")
        else:
            QMessageBox.warning(self, "삭제 실패", "파일을 삭제하는 중 오류가 발생했습니다.")


# --- 유사 이미지 스캔 화면 (UI 클래스) (변경 없음) ---
class SimilarImageScanPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setAcceptDrops(True)
        self.first_file_path = None
        self.initial_text = ("\n\n유사 이미지를 스캔할 폴더를 드롭하거나,\n"
                             "비교할 파일 2개를 하나씩 드롭하세요.\n\n")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        self.info_label = QLabel(self.initial_text)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setMinimumHeight(190)
        slider_box = QFrame()
        slider_box.setFrameShape(QFrame.StyledPanel)
        slider_box.setStyleSheet("background-color: #3A3A3A; border-radius: 4px; padding: 10px;")
        slider_layout = QVBoxLayout(slider_box)
        self.threshold_label = QLabel("유사도 기준: 95% (높을수록 더 비슷해야 함)")
        self.threshold_label.setAlignment(Qt.AlignCenter)
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(80, 100)
        self.threshold_slider.setValue(95)
        self.threshold_slider.valueChanged.connect(self.update_slider_label)
        slider_layout.addWidget(self.threshold_label)
        slider_layout.addWidget(self.threshold_slider)
        self.result_table = QTableWidget()
        self.result_table.setObjectName("ResultTable")
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["파일 경로", "유사도"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.cellClicked.connect(self.show_image_preview)
        left_layout.addWidget(self.info_label)
        left_layout.addStretch(1)
        left_layout.addWidget(slider_box)
        left_layout.addWidget(self.result_table, 3)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        self.two_panel_preview_widget = QWidget()
        preview_layout = QVBoxLayout(self.two_panel_preview_widget)
        preview_layout.setContentsMargins(0,0,0,0)
        self.preview_label_top = QLabel("파일 1을 드롭하세요")
        self.preview_label_top.setAlignment(Qt.AlignCenter)
        self.preview_label_top.setObjectName("ImagePreview")
        self.preview_label_bottom = QLabel("파일 2를 드롭하세요")
        self.preview_label_bottom.setAlignment(Qt.AlignCenter)
        self.preview_label_bottom.setObjectName("ImagePreview")
        preview_layout.addWidget(self.preview_label_top, 1)
        preview_layout.addWidget(self.preview_label_bottom, 1)
        self.single_panel_preview_widget = QWidget()
        single_preview_layout = QVBoxLayout(self.single_panel_preview_widget)
        single_preview_layout.setContentsMargins(0,0,0,0)
        self.single_preview_label = QLabel("테이블에서 이미지를 클릭하세요.")
        self.single_preview_label.setAlignment(Qt.AlignCenter)
        self.single_preview_label.setObjectName("ImagePreview")
        single_preview_layout.addWidget(self.single_preview_label, 1)
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(self.two_panel_preview_widget)
        self.preview_stack.addWidget(self.single_panel_preview_widget)
        reset_btn = QPushButton("다시 하기")
        reset_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        reset_btn.clicked.connect(self.reset_page)
        back_btn = QPushButton("뒤로 가기")
        back_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowBack))
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))
        right_layout.addWidget(self.preview_stack, 1)
        right_layout.addWidget(reset_btn)
        right_layout.addWidget(back_btn)
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)
    def update_slider_label(self, value):
        self.threshold_label.setText(f"유사도 기준: {value}% (높을수록 더 비슷해야 함)")
    def reset_page(self):
        self.first_file_path = None
        self.info_label.setText(self.initial_text)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setStyleSheet("")
        self.result_table.setRowCount(0)
        self.preview_label_top.setText("파일 1을 드롭하세요")
        self.preview_label_bottom.setText("파일 2를 드롭하세요")
        self.single_preview_label.setText("테이블에서 이미지를 클릭하세요.")
        self.preview_label_top.clear()
        self.preview_label_bottom.clear()
        self.single_preview_label.clear()
        self.preview_stack.setCurrentIndex(0)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
            self.info_label.setStyleSheet("border-color: #0078D7; color: #E0E0E0;")
        else: event.ignore()
    def dragLeaveEvent(self, event):
        if self.first_file_path is None: self.reset_page()
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return
        self.result_table.setRowCount(0)
        self.preview_label_top.clear()
        self.preview_label_bottom.clear()
        if len(files) > 1 or os.path.isdir(files[0]):
            self.first_file_path = None
            if len(files) == 1 and os.path.isdir(files[0]):
                self.handle_folder_scan(files[0])
            elif all(os.path.isfile(f) for f in files):
                self.handle_multiple_file_scan(files)
            else:
                self.info_label.setText("⚠️ 폴더는 하나만, 또는 파일만 여러 개 드롭해주세요.\n(폴더와 파일을 섞어 드롭할 수 없습니다.)")
                self.info_label.setAlignment(Qt.AlignCenter)
                self.info_label.setStyleSheet("")
        elif len(files) == 1 and os.path.isfile(files[0]):
            dropped_file_path = files[0]
            if self.first_file_path is None:
                self.first_file_path = dropped_file_path
                filename = os.path.basename(dropped_file_path)
                self.info_label.setText(f"<b>첫 번째 파일 등록됨:</b><br>{filename}<br><br>비교할 두 번째 파일을 드롭하세요.")
                self.info_label.setAlignment(Qt.AlignCenter)
                self.info_label.setStyleSheet("")
                self.show_image_preview_by_path(dropped_file_path, position="top")
            else:
                self.handle_1v1_comparison(self.first_file_path, dropped_file_path)
                self.first_file_path = None
        else:
            self.reset_page()
            self.info_label.setText("⚠️ 유효하지 않은 드롭입니다. 폴더나 파일을 드롭하세요.")
    def handle_1v1_comparison(self, file1, file2):
        self.info_label.setText(f"'{os.path.basename(file1)}'와\n'{os.path.basename(file2)}' 비교 중...")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("")
        QApplication.processEvents()
        ssim_score, phash_sim, hash_diff = app_logic.get_image_similarity(file1, file2)
        if ssim_score is None:
            self.info_label.setText(f"⚠️ 두 파일 비교 중 오류 발생.\n지원되지 않는 이미지 형식이거나 파일이 손상되었습니다.")
        else:
            result_text = (f"<b>1:1 이미지 비교 결과:</b><br><br>"
                           f"<b>파일 1:</b> {os.path.basename(file1)}<br>"
                           f"<b>파일 2:</b> {os.path.basename(file2)}<br><br>"
                           f"구조적 유사도 (SSIM): <font size='+2'><b>{ssim_score:.2f}%</b></font><br>"
                           f"콘텐츠 유사도 (pHash): <font size='+2'><b>{phash_sim:.2f}%</b></font><br>"
                           f"<small>(pHash 차이: {hash_diff} / 64)</small>")
            self.info_label.setText(result_text)
            self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.info_label.setStyleSheet("padding: 15px;")
            group_data = [(file1, 100.0), (file2, phash_sim)]
            self.populate_table([group_data])
            threshold_percent = self.threshold_slider.value()
            if phash_sim >= threshold_percent:
                group_data = [(file1, 100.0), (file2, phash_sim)]
                self.populate_table([group_data])
            else:
                self.result_table.setRowCount(0)
            self.show_image_preview_by_path(file1, position="top")
            self.show_image_preview_by_path(file2, position="bottom")
            self.preview_stack.setCurrentIndex(0)
    def handle_folder_scan(self, folder_path):
        self.info_label.setText(f"'{os.path.basename(folder_path)}' 스캔 중... (시간이 걸릴 수 있습니다)")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("")
        QApplication.processEvents()
        threshold_percent = self.threshold_slider.value()
        hamming_threshold = int(64 * (100 - threshold_percent) / 100)
        similar_groups = app_logic.find_similar_images_from_folder(folder_path, hamming_threshold)
        self.populate_table(similar_groups)
        self.preview_stack.setCurrentIndex(1)
        self.single_preview_label.setText("테이블에서 이미지를 클릭하세요.")
        if not similar_groups: self.info_label.setText("✅ 검사 완료: 유사한 이미지가 없습니다.")
        else: self.info_label.setText(f"검색 완료. 총 {len(similar_groups)}개의 유사 그룹을 찾았습니다.")
    def handle_multiple_file_scan(self, file_list):
        self.info_label.setText(f"총 {len(file_list)}개 파일 스캔 중...")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("")
        QApplication.processEvents()
        threshold_percent = self.threshold_slider.value()
        hamming_threshold = int(64 * (100 - threshold_percent) / 100)
        similar_groups = app_logic.find_similar_images_from_list(file_list, hamming_threshold)
        self.populate_table(similar_groups)
        if not similar_groups: self.info_label.setText("✅ 검사 완료: 유사한 이미지가 없습니다.")
        else: self.info_label.setText(f"검색 완료. 총 {len(similar_groups)}개의 유사 그룹을 찾았습니다.")
    def show_image_preview_by_path(self, file_path, position="top"): 
        if position == "top":
            label = self.preview_label_top
        elif position == "bottom":
            label = self.preview_label_bottom
        else:
            label = self.single_preview_label
        if os.path.exists(file_path):
            try:
                pixmap = QPixmap()
                with open(file_path, 'rb') as f:
                    img_bytes = f.read()
                pixmap.loadFromData(img_bytes)
                label.setPixmap(pixmap.scaled(label.size(), 
                                              Qt.KeepAspectRatio, 
                                              Qt.SmoothTransformation))
            except Exception as e:
                label.setText(f"미리보기 오류:\n{e}")
        else:
            label.setText("파일을 찾을 수 없습니다.")
    def show_image_preview(self, row, column):
        if self.result_table.columnSpan(row, 0) > 1:
            return 
        path_item = self.result_table.item(row, 0) 
        if not path_item: 
            return
        current_preview_mode = self.preview_stack.currentIndex()
        if current_preview_mode == 0:
            standard_path = path_item.data(Qt.UserRole)
            clicked_path = path_item.data(Qt.UserRole + 1)
            if not clicked_path: clicked_path = path_item.text()
            if not standard_path: standard_path = clicked_path
            self.show_image_preview_by_path(standard_path, position="top")
            self.show_image_preview_by_path(clicked_path, position="bottom")
        else:
            clicked_path = path_item.data(Qt.UserRole + 1)
            if not clicked_path: clicked_path = path_item.text()
            self.show_image_preview_by_path(clicked_path, position="single")
    def populate_table(self, groups):
        self.result_table.setRowCount(0)
        for i, group in enumerate(groups):
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            header_item = QTableWidgetItem(f"🖼️ 유사 그룹 {i+1} (총 {len(group)}개)")
            header_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            header_item.setBackground(QColor("#4A4A4A"))
            self.result_table.setSpan(row_position, 0, 1, 2)
            self.result_table.setItem(row_position, 0, header_item)
            for path, similarity in group:
                row_position = self.result_table.rowCount()
                self.result_table.insertRow(row_position)
                path_item = QTableWidgetItem(path)
                if similarity == 100.0:
                    score_item = QTableWidgetItem("기준 (100.0%)")
                    score_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                else:
                    score_item = QTableWidgetItem(f"{similarity:.1f}%")
                self.result_table.setItem(row_position, 0, path_item)
                self.result_table.setItem(row_position, 1, score_item)

# app_ui.py 파일 끝 부분 (MainWindow 클래스 정의 위에)에 다음 클래스를 통째로 추가해야 합니다.

class ImageQualityPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setAcceptDrops(True)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. 왼쪽: 결과 테이블 및 드롭 존
        left_layout = QVBoxLayout()
        self.info_label = QLabel("\n\n이미지 품질을 검사할 폴더를\n이곳으로 드래그 앤 드롭하세요.\n\n")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setMinimumHeight(150)
        
        self.result_table = QTableWidget()
        self.result_table.setObjectName("ResultTable")
        self.result_table.setColumnCount(6)
        
        # 테이블 헤더 정의
        self.result_table.setHorizontalHeaderLabels([
            "파일 경로", "종합 점수", "미적 점수", "기술 점수", "선명도(Lap)", "화질(Brisque)"
        ])

        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            self.result_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        
        left_layout.addWidget(self.info_label, 1)
        left_layout.addWidget(self.result_table, 3)
        
        # 2. 오른쪽: 통계 및 제어 버튼
        right_layout = QVBoxLayout()
        self.stats_label = QLabel("검사할 이미지 파일을 포함한 폴더를 드롭하세요.")
        self.stats_label.setStyleSheet("padding: 10px; background-color: #3A3A3A; border-radius: 4px; min-height: 120px;")
        
        # Matplotlib 캔버스 (MATPLOTLIB_AVAILABLE 여부는 파일 상단에서 정의됨)
        # 이 부분은 사용자 환경에 따라 달라지므로, MplCanvas 정의가 app_ui.py에 있어야 합니다.
        try:
             # 임시로 Matplotlib 캔버스 객체를 만듭니다. (실제 사용 여부는 MATPLOTLIB_AVAILABLE 변수에 따름)
             from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
             from matplotlib.figure import Figure
             class MplCanvas(FigureCanvas): # MplCanvas 클래스가 app_ui.py 파일 상단에 정의되어 있다고 가정합니다.
                def __init__(self, parent=None, width=5, height=4, dpi=100):
                   self.fig = Figure(figsize=(width, height), dpi=dpi)
                   self.axes = self.fig.add_subplot(111)
                   self.fig.patch.set_facecolor('#3A3A3A')
                   super(MplCanvas, self).__init__(self.fig)
                   self.setParent(parent)

             self.canvas = MplCanvas(self, width=5, height=4, dpi=100) if MATPLOTLIB_AVAILABLE else None
        except ImportError:
            self.canvas = None
            
        if self.canvas:
            right_layout.addWidget(self.stats_label, 1)
            right_layout.addWidget(self.canvas, 3)
        else:
            right_layout.addWidget(self.stats_label, 1)

        button_layout = QHBoxLayout()
        reset_btn = QPushButton("다시 하기")
        reset_btn.clicked.connect(self.reset_page)
        back_btn = QPushButton("뒤로 가기")
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))
        
        button_layout.addStretch(1)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(back_btn)
        
        right_layout.addLayout(button_layout)
        
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)
        
    def reset_page(self):
        self.info_label.setText("\n\n이미지 품질을 검사할 폴더를\n이곳으로 드래그 앤 드롭하세요.\n\n")
        self.info_label.setStyleSheet("")
        self.result_table.setRowCount(0)
        self.stats_label.setText("검사할 이미지 파일을 포함한 폴더를 드롭하세요.")
        if MATPLOTLIB_AVAILABLE and self.canvas:
             self.canvas.axes.clear()
             self.canvas.draw()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
            self.info_label.setStyleSheet("border-color: #0078D7; color: #E0E0E0;")
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return
        folder_path = files[0]

        if os.path.isdir(folder_path):
            self.info_label.setText(f"'{os.path.basename(folder_path)}' 폴더 내 이미지 품질 분석 중... (시간 소요)")
            QApplication.processEvents()
            
            # --- 핵심 로직 호출 (app_logic 필요) ---
            results, iqa_active = app_logic.analyze_image_quality_in_folder(folder_path)
            
            if not iqa_active:
                 self.info_label.setText("❌ AI 모델 로드 실패: 품질 검사 기능이 비활성화되었습니다.")
                 return

            if not results:
                self.info_label.setText("✅ 검사 완료: 폴더 내에 이미지 파일이 없습니다.")
            else:
                self.populate_table(results)
                self.info_label.setText(f"✅ 검사 완료: 총 {len(results)}개 이미지의 품질을 분석했습니다.")
                
        else:
            self.info_label.setText("⚠️ 폴더가 아닙니다. 폴더를 드래그 앤 드롭해주세요.")

    def populate_table(self, results):
        self.result_table.setRowCount(0)
        
        for rank, data in enumerate(results):
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            
            # 파일 경로
            path_item = QTableWidgetItem(data['path'])
            
            # 최종 점수
            final_score_item = QTableWidgetItem(f"{data['score_data']['final_score']:.2f}")
            
            # 미적/기술 점수 (breakdown)
            aes_item = QTableWidgetItem(f"{data['score_data']['aesthetic']:.2f}")
            tech_item = QTableWidgetItem(f"{data['score_data']['technical']:.2f}")
            
            # 원본 지표
            lap_item = QTableWidgetItem(f"{data['score_data']['raw_metrics']['raw_laplacian']:.0f}")
            brisque_item = QTableWidgetItem(f"{data['score_data']['raw_metrics']['raw_brisque']:.0f}")

            # 1위 강조
            if rank == 0:
                 path_item.setForeground(QColor("#FFD700"))
                 final_score_item.setForeground(QColor("#FFD700"))
                 final_score_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                 for col in range(6):
                    cell = self.result_table.item(row_position, col)
                    if cell: cell.setBackground(QColor("#444430"))
            
            self.result_table.setItem(row_position, 0, path_item)
            self.result_table.setItem(row_position, 1, final_score_item)
            self.result_table.setItem(row_position, 2, aes_item)
            self.result_table.setItem(row_position, 3, tech_item)
            self.result_table.setItem(row_position, 4, lap_item)
            self.result_table.setItem(row_position, 5, brisque_item)
            
            for i in range(1, 6):
                 item = self.result_table.item(row_position, i)
                 item.setTextAlignment(Qt.AlignCenter)

# --- 메인 윈도우 (UI 클래스) (변경 없음) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("파일 유틸리티 Pro")
        self.setGeometry(200, 200, 1000, 650) 
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.start_page = StartPage(self.stacked_widget)
        self.duplicate_page = DuplicateCheckPage(self.stacked_widget)
        self.similar_image_page = SimilarImageScanPage(self.stacked_widget)
        self.iqa_page = ImageQualityPage(self.stacked_widget)
        self.stacked_widget.addWidget(self.start_page)
        self.stacked_widget.addWidget(self.duplicate_page)
        self.stacked_widget.addWidget(self.similar_image_page)
        self.stacked_widget.addWidget(self.iqa_page)

# --- 애플리케이션 실행 (변경 없음) ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    style_file_path = os.path.join(base_dir, "style.qss")
    
    print(f"스타일시트 로드 시도: {style_file_path}")
    
    style_str = load_stylesheet(style_file_path)
    
    if style_str:
        app.setStyleSheet(style_str)
        print("스타일시트 적용 성공.")
    else:
        print("스타일시트 적용 실패. (파일을 찾지 못했거나 내용이 비어있습니다)")
    
    # 다크 팔레트 적용
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())