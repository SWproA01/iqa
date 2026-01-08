# 파일 이름: app_ui.py

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QFrame,
                             QMessageBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QHBoxLayout, QStyle, QSlider, QGridLayout, QTextEdit,
                             QCheckBox, QSizePolicy)
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


# --- 메인 드롭/분석 화면 (UI 클래스) ---
class MainDropAnalyzePage(QWidget):
    """
    앱 실행 시 처음 보이는 메인 페이지.
    1. 파일/폴더 드롭존
    2. 드롭 시 파일 목록/간단 통계 표시
    3. 하단에 기능 버튼들(중복, 유사 이미지, 비디오, 문서, 품질, 통합)
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setAcceptDrops(True)
        self.dropped_files = []
        self.folder_path = None
        self.current_analysis_type = None  # 현재 분석 타입 저장
        self.current_duplicates = {}  # 중복 검사 결과 저장
        self.current_similar_groups = []  # 유사도 검사 결과 저장
        self.current_quality_results = []  # 품질 검사 결과 저장
        self.first_selected_image = None  # 유사 이미지 비교 첫 선택
        self.first_selected_doc = None  # 문서 유사도 비교 첫 선택
        self.first_selected_video = None  # 비디오 유사도 비교 첫 선택

        # 메인 레이아웃 (좌우 분할)
        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(20, 20, 20, 20)
        main_h_layout.setSpacing(15)

        # === 좌측 영역 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # 타이틀
        title = QLabel("하루 정리")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)

        # 1. 안내 및 드롭존
        self.info_label = QLabel("\n\n분석할 폴더 또는 파일을\n여기에 드래그 앤 드롭하세요.\n\n")
        self.info_label.setObjectName("DropZone")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setMinimumHeight(100)
        left_layout.addWidget(self.info_label)

        # 2. 파일 목록/간단 통계
        self.result_table = QTableWidget()
        self.result_table.setObjectName("ResultTable")
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["파일 경로", "크기"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setMinimumHeight(150)
        left_layout.addWidget(self.result_table)

        # 3. 통계 (간단)
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignLeft)
        self.stats_label.setStyleSheet("background: #CDF5FD; border-radius: 6px; padding: 8px;")
        left_layout.addWidget(self.stats_label)

        # 4. 하단 기능 버튼들 (가로 한 줄)
        btn_label = QLabel("수행할 작업을 선택하세요:")
        btn_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #012433;")
        left_layout.addWidget(btn_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_dup = QPushButton("중복 파일")
        self.btn_dup.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogYesButton))
        self.btn_dup.clicked.connect(self.run_duplicate_check)
        
        self.btn_simimg = QPushButton("유사 이미지")
        self.btn_simimg.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.btn_simimg.clicked.connect(self.run_similar_image)
        
        self.btn_iqa = QPushButton("이미지 품질")
        self.btn_iqa.setIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
        self.btn_iqa.clicked.connect(self.run_image_quality)
        
        self.btn_simvid = QPushButton("비디오 유사도")
        self.btn_simvid.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_simvid.clicked.connect(self.run_similar_video)
        
        self.btn_simdoc = QPushButton("문서 유사도")
        self.btn_simdoc.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.btn_simdoc.clicked.connect(self.run_similar_doc)

        for btn in [self.btn_dup, self.btn_simimg, self.btn_iqa, self.btn_simvid, self.btn_simdoc]:
            btn.setMinimumHeight(40)
            btn_layout.addWidget(btn)
        
        left_layout.addLayout(btn_layout)

        # 5. 분석 결과 표시 영역 (좌측 하단)
        result_label = QLabel("분석 결과:")
        result_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #012433;")
        left_layout.addWidget(result_label)

        self.analysis_result_table = QTableWidget()
        self.analysis_result_table.setObjectName("ResultTable")
        self.analysis_result_table.setColumnCount(4)
        self.analysis_result_table.setHorizontalHeaderLabels(["선택", "항목", "값", "세부사항"])
        self.analysis_result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.analysis_result_table.setColumnWidth(0, 50)
        self.analysis_result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.analysis_result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.analysis_result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.analysis_result_table.setAlternatingRowColors(True)
        self.analysis_result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.analysis_result_table.setMinimumHeight(300)
        self.analysis_result_table.itemDoubleClicked.connect(self.on_result_item_double_clicked)
        left_layout.addWidget(self.analysis_result_table)

        # 결과 처리 버튼들 (삭제 등)
        action_layout = QHBoxLayout()
        self.delete_btn = QPushButton("선택 파일 삭제")
        self.delete_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_TrashIcon))
        self.delete_btn.clicked.connect(self.delete_selected_files)
        action_layout.addStretch(1)
        action_layout.addWidget(self.delete_btn)
        left_layout.addLayout(action_layout)

        # === 우측 영역 (시각화) ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        viz_label = QLabel("상세 정보")
        viz_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #012433;")
        right_layout.addWidget(viz_label)

        # 스택 위젯으로 다양한 시각화 전환
        self.viz_stack = QStackedWidget()
        
        # 0: 기본 안내 화면
        default_label = QLabel("좌측에서 분석을 실행하면\n상세 정보가 여기에 표시됩니다.")
        default_label.setAlignment(Qt.AlignCenter)
        default_label.setStyleSheet("color: #888; font-size: 11pt;")
        self.viz_stack.addWidget(default_label)
        
        # 1: 중복 검사 - 원형 그래프 (Matplotlib)
        if MATPLOTLIB_AVAILABLE:
            self.dup_canvas = MplCanvas(self, width=6, height=6, dpi=100)
            self.viz_stack.addWidget(self.dup_canvas)
        else:
            no_graph_label = QLabel("그래프를 표시할 수 없습니다.\nMatplotlib을 설치해주세요.")
            no_graph_label.setAlignment(Qt.AlignCenter)
            self.viz_stack.addWidget(no_graph_label)
        
        # 2: 유사 이미지 - 이미지 비교 뷰
        self.img_compare_widget = QWidget()
        img_compare_layout = QVBoxLayout(self.img_compare_widget)
        self.img_preview_top = QLabel("이미지 1")
        self.img_preview_top.setAlignment(Qt.AlignCenter)
        self.img_preview_top.setStyleSheet("border: 2px solid #00A9FF; background: #E8E8E8;")
        self.img_preview_top.setMinimumHeight(200)
        self.img_preview_bottom = QLabel("이미지 2")
        self.img_preview_bottom.setAlignment(Qt.AlignCenter)
        self.img_preview_bottom.setStyleSheet("border: 2px solid #00A9FF; background: #E8E8E8;")
        self.img_preview_bottom.setMinimumHeight(200)
        img_compare_layout.addWidget(self.img_preview_top)
        img_compare_layout.addWidget(self.img_preview_bottom)
        self.viz_stack.addWidget(self.img_compare_widget)
        
        # 3: 문서 유사도 - 텍스트 미리보기 (2개 영역)
        self.doc_compare_widget = QWidget()
        doc_compare_layout = QVBoxLayout(self.doc_compare_widget)
        
        doc_top_label = QLabel("🔷 첫 번째 문서")
        doc_top_label.setStyleSheet("font-weight: bold; color: #00A9FF; font-size: 10pt;")
        self.doc_preview_top = QTextEdit()
        self.doc_preview_top.setReadOnly(True)
        self.doc_preview_top.setPlaceholderText("첫 번째 문서를 선택하세요.")
        self.doc_preview_top.setStyleSheet("border: 2px solid #00A9FF; background: #FFFFFF;")
        
        doc_bottom_label = QLabel("🔷 두 번째 문서")
        doc_bottom_label.setStyleSheet("font-weight: bold; color: #89CFF3; font-size: 10pt;")
        self.doc_preview_bottom = QTextEdit()
        self.doc_preview_bottom.setReadOnly(True)
        self.doc_preview_bottom.setPlaceholderText("두 번째 문서를 선택하세요.")
        self.doc_preview_bottom.setStyleSheet("border: 2px solid #89CFF3; background: #FFFFFF;")
        
        doc_compare_layout.addWidget(doc_top_label)
        doc_compare_layout.addWidget(self.doc_preview_top, 1)
        doc_compare_layout.addWidget(doc_bottom_label)
        doc_compare_layout.addWidget(self.doc_preview_bottom, 1)
        
        self.viz_stack.addWidget(self.doc_compare_widget)
        
        # 4: 비디오 유사도 - 비디오 정보 2개 영역
        self.video_compare_widget = QWidget()
        video_compare_layout = QVBoxLayout(self.video_compare_widget)
        
        video_top_label = QLabel("🔷 첫 번째 비디오")
        video_top_label.setStyleSheet("font-weight: bold; color: #00A9FF; font-size: 10pt;")
        self.video_preview_top = QLabel("첫 번째 비디오를 더블클릭하세요.")
        self.video_preview_top.setAlignment(Qt.AlignCenter)
        self.video_preview_top.setStyleSheet("border: 3px solid #00A9FF; background: #E8E8E8; padding: 10px; font-size: 10pt; color: #555;")
        
        video_bottom_label = QLabel("🔷 두 번째 비디오")
        video_bottom_label.setStyleSheet("font-weight: bold; color: #89CFF3; font-size: 10pt;")
        self.video_preview_bottom = QLabel("두 번째 비디오를 더블클릭하세요.")
        self.video_preview_bottom.setAlignment(Qt.AlignCenter)
        self.video_preview_bottom.setStyleSheet("border: 3px solid #89CFF3; background: #E8E8E8; padding: 10px; font-size: 10pt; color: #555;")
        
        video_compare_layout.addWidget(video_top_label)
        video_compare_layout.addWidget(self.video_preview_top, 1)
        video_compare_layout.addWidget(video_bottom_label)
        video_compare_layout.addWidget(self.video_preview_bottom, 1)
        
        self.viz_stack.addWidget(self.video_compare_widget)
        
        right_layout.addWidget(self.viz_stack)
        
        # 좌우 배치 (6:4 비율)
        main_h_layout.addWidget(left_widget, 5)
        main_h_layout.addWidget(right_widget, 7)

        self.first_selected_doc = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files:
            return
        self.dropped_files = files
        self.folder_path = files[0] if os.path.isdir(files[0]) else os.path.dirname(files[0])
        self.show_file_list(files)
        self.show_stats(files)
        self.info_label.setText("✅ 파일 로드 완료!\n아래에서 원하는 기능을 선택하세요.")

    def show_file_list(self, files):
        self.result_table.setRowCount(0)
        # 폴더인 경우 내부 파일들을 수집
        all_files = []
        for f in files:
            if os.path.isdir(f):
                for root, dirs, filenames in os.walk(f):
                    for fname in filenames:
                        all_files.append(os.path.join(root, fname))
            else:
                all_files.append(f)
        
        # 최대 100개만 표시
        display_files = all_files[:100]
        for f in display_files:
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
            self.result_table.setItem(row, 0, QTableWidgetItem(f))
            try:
                size = os.path.getsize(f) if os.path.isfile(f) else 0
            except Exception:
                size = 0
            self.result_table.setItem(row, 1, QTableWidgetItem(app_logic.format_bytes(size)))
        
        if len(all_files) > 100:
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
            self.result_table.setItem(row, 0, QTableWidgetItem(f"... 외 {len(all_files) - 100}개 파일"))
            self.result_table.setItem(row, 1, QTableWidgetItem(""))

    def show_stats(self, files):
        all_files = []
        for f in files:
            if os.path.isdir(f):
                for root, dirs, filenames in os.walk(f):
                    for fname in filenames:
                        all_files.append(os.path.join(root, fname))
            else:
                all_files.append(f)
        
        total = len(all_files)
        total_size = sum(os.path.getsize(f) for f in all_files if os.path.isfile(f))
        self.stats_label.setText(
            f"📊 <b>총 파일 수:</b> {total}개 | <b>총 용량:</b> {app_logic.format_bytes(total_size)}"
        )

    def run_duplicate_check(self):
        """중복 파일 검사 실행"""
        if not self.folder_path:
            QMessageBox.warning(self, "경고", "먼저 폴더를 드래그 앤 드롭해주세요.")
            return
        
        self.info_label.setText("🔄 중복 파일 검사 중...")
        QApplication.processEvents()
        
        try:
            duplicates, total_files, total_size = app_logic.find_duplicate_files(self.folder_path)
            self.current_analysis_type = "duplicate"
            self.current_duplicates = duplicates
            self.display_duplicate_results(duplicates, total_files, total_size)
            self.draw_duplicate_pie_chart(duplicates, total_files)
            self.viz_stack.setCurrentIndex(1)  # 원형 그래프 표시
            self.info_label.setText(f"✅ 중복 파일 검사 완료")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"중복 파일 검사 중 오류 발생:\n{str(e)}")
            self.info_label.setText("❌ 검사 실패")

    def run_similar_image(self):
        """유사 이미지 검사 실행"""
        if not self.folder_path:
            QMessageBox.warning(self, "경고", "먼저 폴더를 드래그 앤 드롭해주세요.")
            return
        
        self.info_label.setText("🔄 유사 이미지 분석 중...")
        QApplication.processEvents()
        
        try:
            threshold = 10  # 기본값
            groups = app_logic.find_similar_images_from_folder(self.folder_path, threshold)
            self.current_analysis_type = "similar_image"
            self.current_similar_groups = groups
            self.display_similar_groups(groups, "이미지")
            self.viz_stack.setCurrentIndex(2)  # 이미지 비교 뷰 표시
            self.info_label.setText(f"✅ 유사 이미지 분석 완료")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"유사 이미지 분석 중 오류 발생:\n{str(e)}")
            self.info_label.setText("❌ 분석 실패")

    def run_image_quality(self):
        """이미지 품질 분석 실행"""
        if not self.folder_path:
            QMessageBox.warning(self, "경고", "먼저 폴더를 드래그 앤 드롭해주세요.")
            return
        
        self.info_label.setText("🔄 이미지 품질 분석 중...")
        QApplication.processEvents()
        
        try:
            results, success = app_logic.analyze_image_quality_in_folder(self.folder_path)
            if success:
                self.current_analysis_type = "image_quality"
                self.current_quality_results = results  # 품질 결과 저장
                self.display_quality_results(results)
                self.viz_stack.setCurrentIndex(2)  # 이미지 뷰 표시
                self.info_label.setText(f"✅ 이미지 품질 분석 완료")
            else:
                QMessageBox.warning(self, "경고", "이미지 품질 분석 기능을 사용할 수 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"이미지 품질 분석 중 오류 발생:\n{str(e)}")
            self.info_label.setText("❌ 분석 실패")

    def run_similar_video(self):
        """유사 비디오 검사 실행"""
        if not self.folder_path:
            QMessageBox.warning(self, "경고", "먼저 폴더를 드래그 앤 드롭해주세요.")
            return
        
        self.info_label.setText("🔄 유사 비디오 분석 중...")
        QApplication.processEvents()
        
        try:
            threshold = 60  # 기본값
            groups = app_logic.find_similar_videos_from_folder(self.folder_path, threshold)
            self.current_analysis_type = "similar_video"
            self.current_similar_groups = groups
            self.display_similar_groups(groups, "비디오")
            self.viz_stack.setCurrentIndex(4)  # 비디오 비교 뷰 표시
            self.info_label.setText(f"✅ 유사 비디오 분석 완료")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"유사 비디오 분석 중 오류 발생:\n{str(e)}")
            self.info_label.setText("❌ 분석 실패")

    def run_similar_doc(self):
        """유사 문서 검사 실행"""
        if not self.folder_path:
            QMessageBox.warning(self, "경고", "먼저 폴더를 드래그 앤 드롭해주세요.")
            return
        
        self.info_label.setText("🔄 유사 문서 분석 중...")
        QApplication.processEvents()
        
        try:
            threshold = 75  # 기본값
            groups = app_logic.find_similar_docs_from_folder(self.folder_path, threshold)
            self.current_analysis_type = "similar_doc"
            self.current_similar_groups = groups
            self.display_similar_groups(groups, "문서")
            self.viz_stack.setCurrentIndex(3)  # 문서 미리보기 표시
            self.info_label.setText(f"✅ 유사 문서 분석 완료")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"유사 문서 분석 중 오류 발생:\n{str(e)}")
            self.info_label.setText("❌ 분석 실패")

    def display_duplicate_results(self, duplicates, total_files, total_size):
        """중복 파일 결과 표시 (그룹 없이 개별 행)"""
        self.analysis_result_table.setRowCount(0)
        group_index = 1
        for hash_val, paths in duplicates.items():
            for p in paths:
                row = self.analysis_result_table.rowCount()
                self.analysis_result_table.insertRow(row)
                
                # 체크박스 추가
                checkbox_widget = QWidget()
                chk_layout = QHBoxLayout(checkbox_widget)
                chk_box = QCheckBox()
                chk_layout.addWidget(chk_box)
                chk_layout.setAlignment(Qt.AlignCenter)
                chk_layout.setContentsMargins(0, 0, 0, 0)
                chk_box.setProperty("file_path", p)
                self.analysis_result_table.setCellWidget(row, 0, checkbox_widget)
                
                self.analysis_result_table.setItem(row, 1, QTableWidgetItem(os.path.basename(p)))
                self.analysis_result_table.setItem(row, 2, QTableWidgetItem(f"중복 #{group_index}"))
                details_item = QTableWidgetItem(p)
                details_item.setData(Qt.UserRole, [p])
                self.analysis_result_table.setItem(row, 3, details_item)
            group_index += 1

    def display_similar_groups(self, groups, type_name):
        """유사 파일 그룹 결과 표시 (그룹 없이 개별 행)"""
        self.analysis_result_table.setRowCount(0)
        for group in groups:
            if isinstance(group, dict):
                norm_paths = list(group.keys())
            elif isinstance(group, list) and len(group) > 0 and isinstance(group[0], tuple):
                norm_paths = [item[0] for item in group]
            else:
                norm_paths = list(group)
            for p in norm_paths:
                row = self.analysis_result_table.rowCount()
                self.analysis_result_table.insertRow(row)
                
                # 체크박스 추가
                checkbox_widget = QWidget()
                chk_layout = QHBoxLayout(checkbox_widget)
                chk_box = QCheckBox()
                chk_layout.addWidget(chk_box)
                chk_layout.setAlignment(Qt.AlignCenter)
                chk_layout.setContentsMargins(0, 0, 0, 0)
                chk_box.setProperty("file_path", p)
                self.analysis_result_table.setCellWidget(row, 0, checkbox_widget)
                
                self.analysis_result_table.setItem(row, 1, QTableWidgetItem(os.path.basename(p)))
                self.analysis_result_table.setItem(row, 2, QTableWidgetItem(f"유사 {type_name}"))
                details_item = QTableWidgetItem(p)
                details_item.setData(Qt.UserRole, [p])
                details_item.setData(Qt.UserRole + 1, norm_paths)
                self.analysis_result_table.setItem(row, 3, details_item)

    def display_quality_results(self, results):
        """이미지 품질 결과 표시"""
        self.analysis_result_table.setRowCount(0)
        
        if not results:
            row = self.analysis_result_table.rowCount()
            self.analysis_result_table.insertRow(row)
            self.analysis_result_table.setItem(row, 1, QTableWidgetItem("결과 없음"))
            self.analysis_result_table.setItem(row, 2, QTableWidgetItem(""))
            self.analysis_result_table.setItem(row, 3, QTableWidgetItem(""))
            return
        
        # 상위 20개 표시
        for i, result in enumerate(results[:20], 1):
            row = self.analysis_result_table.rowCount()
            self.analysis_result_table.insertRow(row)
            # 키 이름 확인 (file_path 또는 다른 이름일 수 있음)
            file_path = result.get('file_path') or result.get('path') or result.get('filepath', '')
            filename = os.path.basename(file_path) if file_path else '알 수 없음'
            score = result.get('score_data', {}).get('final_score', 0)
            technical = result.get('score_data', {}).get('technical', 0)
            aesthetic = result.get('score_data', {}).get('aesthetic', 0)
            
            # 체크박스 추가
            checkbox_widget = QWidget()
            chk_layout = QHBoxLayout(checkbox_widget)
            chk_box = QCheckBox()
            chk_layout.addWidget(chk_box)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            if file_path:
                chk_box.setProperty("file_path", file_path)
            self.analysis_result_table.setCellWidget(row, 0, checkbox_widget)
            
            self.analysis_result_table.setItem(row, 1, QTableWidgetItem(f"#{i}"))
            self.analysis_result_table.setItem(row, 2, QTableWidgetItem(f"{score:.1f}점"))
            detail_text = f"{filename}\n기술: {technical:.1f} | 미적: {aesthetic:.1f}"
            details_item = QTableWidgetItem(detail_text)
            # 삭제 기능을 위해 파일 경로 저장
            if file_path:
                details_item.setData(Qt.UserRole, [file_path])
            self.analysis_result_table.setItem(row, 3, details_item)

    def delete_selected_files(self):
        # 체크된 파일 경로 수집
        paths = []
        checked_rows = []
        for row in range(self.analysis_result_table.rowCount()):
            cell_widget = self.analysis_result_table.cellWidget(row, 0)
            if cell_widget:
                chk_box = cell_widget.findChild(QCheckBox)
                if chk_box and chk_box.isChecked():
                    file_path = chk_box.property("file_path")
                    if file_path:
                        paths.append(file_path)
                        checked_rows.append(row)
        
        if not paths:
            QMessageBox.information(self, "알림", "삭제할 파일을 선택하세요.")
            return
        # 중복 제거
        unique_paths = []
        seen = set()
        for p in paths:
            if p not in seen:
                unique_paths.append(p)
                seen.add(p)
        # 확인 대화상자
        preview = "\n".join(os.path.basename(p) for p in unique_paths[:10])
        more = "" if len(unique_paths) <= 10 else f"\n외 {len(unique_paths)-10}개"
        reply = QMessageBox.question(
            self,
            "파일 삭제 확인",
            f"총 {len(unique_paths)}개 파일을 삭제하시겠습니까?\n\n{preview}{more}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        # 삭제 수행
        errors = []
        deleted = 0
        for p in unique_paths:
            try:
                if os.path.isfile(p):
                    os.remove(p)
                    deleted += 1
                else:
                    errors.append(f"파일이 존재하지 않습니다: {p}")
            except Exception as e:
                errors.append(f"삭제 실패: {p} -> {e}")
        # 테이블에서 체크된 행 제거
        for r in sorted(checked_rows, reverse=True):
            self.analysis_result_table.removeRow(r)
        # 통계 갱신
        if self.folder_path and os.path.isdir(self.folder_path):
            try:
                self.show_stats([self.folder_path])
            except Exception:
                pass
        # 결과 알림
        if errors:
            QMessageBox.warning(self, "일부 삭제 실패", f"삭제: {deleted}개, 실패: {len(errors)}개\n\n" + "\n".join(errors[:10]))
        else:
            QMessageBox.information(self, "삭제 완료", f"총 {deleted}개 파일을 삭제했습니다.")

    def draw_duplicate_pie_chart(self, duplicates, total_files):
        """중복 파일 통계를 확장자별로 원형 그래프로 표시"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        total_dup_files = sum(len(paths) for paths in duplicates.values())
        unique_files = total_files - total_dup_files
        
        self.dup_canvas.axes.clear()
        self.dup_canvas.figure.patch.set_facecolor('#EAF8FF')
        self.dup_canvas.axes.set_facecolor('#EAF8FF')
        
        if total_dup_files == 0:
            self.dup_canvas.axes.text(0.5, 0.5, '중복 파일 없음', 
                                     ha='center', va='center', fontsize=14, color='#012433')
            self.dup_canvas.axes.axis('off')
        else:
            # 확장자별 중복 파일 개수 집계
            ext_count = {}
            for hash_val, paths in duplicates.items():
                for path in paths:
                    ext = os.path.splitext(path)[1].lower()
                    if not ext:
                        ext = '.기타'
                    ext_count[ext] = ext_count.get(ext, 0) + 1
            
            # 확장자별로 정렬 (개수 많은 순)
            sorted_exts = sorted(ext_count.items(), key=lambda x: x[1], reverse=True)
            
            # 상위 8개 확장자만 표시, 나머지는 '기타'로 묶기
            max_display = 8
            if len(sorted_exts) > max_display:
                main_exts = sorted_exts[:max_display]
                other_count = sum(count for ext, count in sorted_exts[max_display:])
                if other_count > 0:
                    main_exts.append(('기타', other_count))
            else:
                main_exts = sorted_exts
            
            # 고유 파일 추가
            labels = []
            sizes = []
            colors_list = []
            
            # 색상 팔레트 정의
            ext_colors = [
                '#FF6B6B', '#4ECDC4', '#FFD93D', '#95E1D3', 
                '#F38181', '#AA96DA', '#FCBAD3', '#A8D8EA',
                '#FFAAA5', '#FFD3B6'
            ]
            
            # 고유 파일
            labels.append(f'고유 파일\n({unique_files}개)')
            sizes.append(unique_files)
            colors_list.append('#A0E9FF')
            
            # 확장자별 중복 파일
            for i, (ext, count) in enumerate(main_exts):
                ext_display = ext.upper() if ext.startswith('.') else ext
                labels.append(f'{ext_display}\n({count}개)')
                sizes.append(count)
                colors_list.append(ext_colors[i % len(ext_colors)])
            
            # 원형 그래프 생성
            wedges, texts, autotexts = self.dup_canvas.axes.pie(
                sizes,
                labels=labels,
                colors=colors_list,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 8, 'color': '#012433', 'weight': 'bold'},
                pctdistance=0.85
            )
            
            # 퍼센트 텍스트 스타일
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)
            
            # 레이블 텍스트 스타일
            for text in texts:
                text.set_fontsize(8)
                text.set_color('#012433')
            
            self.dup_canvas.axes.set_title(
                f'중복 파일 분석 (총 {total_files}개, {len(duplicates)}개 그룹)', 
                fontsize=11, fontweight='bold', color='#012433', pad=20
            )
        
        self.dup_canvas.draw()

    def on_result_item_double_clicked(self, item):
        """결과 테이블 항목 더블클릭 시 상세 정보 표시"""
        row = item.row()
        
        if self.current_analysis_type == "similar_image":
            # 행에서 경로 추출 (4열 UserRole에 단일 경로 저장됨)
            path_item = self.analysis_result_table.item(row, 3)
            clicked_path = None
            if path_item:
                data = path_item.data(Qt.UserRole)
                if isinstance(data, list) and data:
                    clicked_path = data[0]
                elif isinstance(data, str):
                    clicked_path = data
            if not clicked_path:
                return

            # 더블클릭 시 이미지 비교 표시
            if not self.first_selected_image:
                self.first_selected_image = clicked_path
                # 첫 번째 이미지만 표시
                pixmap = QPixmap(clicked_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(self.img_preview_top.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    filename = os.path.basename(clicked_path)
                    
                    # 위쪽: 첫 번째 이미지 표시
                    self.img_preview_top.setPixmap(scaled)
                    self.img_preview_top.setText("")  # 텍스트 제거하여 이미지만 표시
                    self.img_preview_top.setStyleSheet(
                        "border: 4px solid #00A9FF; background: #E8E8E8; padding: 5px;"
                    )
                    self.img_preview_top.setAlignment(Qt.AlignCenter)
                    
                    # 아래쪽: 안내 메시지
                    self.img_preview_bottom.clear()
                    self.img_preview_bottom.setPixmap(QPixmap())
                    self.img_preview_bottom.setText(
                        f"✅ 첫 번째 선택: {filename}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━\n\n"
                        "🖼️ 두 번째 이미지를\n더블클릭하여 선택하세요"
                    )
                    self.img_preview_bottom.setStyleSheet(
                        "border: 2px dashed #89CFF3; background: #F0F8FF; "
                        "padding: 20px; font-size: 11pt; color: #0078D7; font-weight: bold;"
                    )
                    self.img_preview_bottom.setAlignment(Qt.AlignCenter)
            else:
                self.show_image_comparison(self.first_selected_image, clicked_path)
                self.first_selected_image = None  # 다음 비교를 위해 초기화
        
        elif self.current_analysis_type == "similar_doc":
            # 유사 문서: 첫 번째/두 번째 선택 처리
            details_item = self.analysis_result_table.item(row, 3)
            if details_item:
                clicked_path = details_item.data(Qt.UserRole)
                if isinstance(clicked_path, list) and clicked_path:
                    clicked_path = clicked_path[0]
                
                if not self.first_selected_doc:
                    # 첫 번째 문서 선택
                    self.first_selected_doc = clicked_path
                    self.show_document_preview(clicked_path)
                else:
                    # 두 번째 문서 선택 - 비교 실행
                    self.show_document_comparison(self.first_selected_doc, clicked_path)
                    self.first_selected_doc = None  # 초기화
        
        elif self.current_analysis_type == "similar_video":
            # 유사 비디오: 첫 번째/두 번째 선택 처리
            details_item = self.analysis_result_table.item(row, 3)
            if details_item:
                clicked_path = details_item.data(Qt.UserRole)
                if isinstance(clicked_path, list) and clicked_path:
                    clicked_path = clicked_path[0]
                
                if not self.first_selected_video:
                    # 첫 번째 비디오 선택
                    self.first_selected_video = clicked_path
                    self.show_video_info(clicked_path)
                else:
                    # 두 번째 비디오 선택 - 비교 실행
                    self.compare_videos(self.first_selected_video, clicked_path)
                    self.first_selected_video = None  # 초기화
        
        elif self.current_analysis_type == "image_quality":
            # 이미지 품질: 선택한 이미지와 상세 점수 표시
            if row < len(self.current_quality_results):
                result = self.current_quality_results[row]
                file_path = result.get('file_path') or result.get('path') or result.get('filepath', '')
                if file_path:
                    self.show_quality_image_detail(file_path, result)

    def show_image_comparison(self, img_path1, img_path2):
        """두 이미지를 비교하여 표시"""
        try:
            # 유사도 계산
            similarity_info = ""
            if img_path1 != img_path2:
                ssim_score, phash_sim, hash_diff = app_logic.get_image_similarity(img_path1, img_path2)
                if ssim_score is not None and phash_sim is not None:
                    similarity_info = f"📊 유사도: {phash_sim:.2f}%"
            
            # 첫 번째 이미지
            pixmap1 = QPixmap(img_path1)
            if not pixmap1.isNull():
                scaled1 = pixmap1.scaled(self.img_preview_top.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_preview_top.setPixmap(scaled1)
                self.img_preview_top.setText("")  # 이미지만 표시
                filename1 = os.path.basename(img_path1)
                self.img_preview_top.setToolTip(f"🖼️ 첫 번째 이미지\n{filename1}")
                self.img_preview_top.setStyleSheet(
                    "border: 4px solid #00A9FF; background: #E8E8E8; padding: 5px;"
                )
                self.img_preview_top.setAlignment(Qt.AlignCenter)
            else:
                self.img_preview_top.clear()
                self.img_preview_top.setText(f"🖼️ 첫 번째 이미지\n\n이미지 로드 실패:\n{os.path.basename(img_path1)}")
                self.img_preview_top.setStyleSheet(
                    "border: 4px solid #00A9FF; background: #F0F8FF; padding: 10px; color: #0078D7;"
                )
            
            # 두 번째 이미지
            pixmap2 = QPixmap(img_path2)
            if not pixmap2.isNull():
                scaled2 = pixmap2.scaled(self.img_preview_bottom.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_preview_bottom.setPixmap(scaled2)
                self.img_preview_bottom.setText("")  # 이미지만 표시
                filename2 = os.path.basename(img_path2)
                tooltip_text = f"🖼️ 두 번째 이미지\n{filename2}"
                if similarity_info:
                    tooltip_text += f"\n\n{similarity_info}"
                self.img_preview_bottom.setToolTip(tooltip_text)
                self.img_preview_bottom.setStyleSheet(
                    "border: 4px solid #89CFF3; background: #E8E8E8; padding: 5px;"
                )
                self.img_preview_bottom.setAlignment(Qt.AlignCenter)
            else:
                self.img_preview_bottom.clear()
                self.img_preview_bottom.setText(f"🖼️ 두 번째 이미지\n\n이미지 로드 실패:\n{os.path.basename(img_path2)}")
                self.img_preview_bottom.setStyleSheet(
                    "border: 4px solid #89CFF3; background: #F0F8FF; padding: 10px; color: #0078D7;"
                )
            
            # 유사도 정보를 info_label에 표시
            if similarity_info:
                self.info_label.setText(f"<b>이미지 비교 결과</b><br><br>{similarity_info}")
                self.info_label.setStyleSheet("padding: 15px; font-size: 11pt; background: #E8F4F8; border-radius: 8px; color: #012433;")
                self.info_label.setAlignment(Qt.AlignCenter)
                
        except Exception as e:
            self.img_preview_top.setText(f"오류: {str(e)}")
            self.img_preview_bottom.setText("")



    def show_document_preview(self, doc_path, is_first=True):
        """첫 번째 문서 선택 시 호출: 위쪽 박스 채우기 + 안내 메시지"""
        filename = os.path.basename(doc_path)
        try:
            # 텍스트 추출
            preview_text = app_logic.extract_text_from_file(doc_path, max_chars=1500)
            
            # 위쪽 박스 (첫 번째 문서)
            self.doc_preview_top.setText(f"📄 파일명: {filename}\n{'='*40}\n\n{preview_text}")
            
            # 아래쪽 박스 (안내 문구)
            self.doc_preview_bottom.clear()
            self.doc_preview_bottom.setPlaceholderText("비교할 두 번째 문서를 목록에서 더블클릭하세요.")
            
            # 중앙 안내 문구 업데이트
            self.info_label.setText(
                f"<div style='font-size: 11pt; font-weight: bold;'>✅ 첫 번째 문서 선택됨</div><br>"
                f"두 번째 문서를 더블클릭하세요"
            )
            self.info_label.setStyleSheet("padding: 20px; background: #E8F4F8; border: 3px solid #00A9FF; border-radius: 8px; color: #012433;")
            
        except Exception as e:
            self.doc_preview_top.setText(f"문서 미리보기 오류: {str(e)}")

    def show_document_comparison(self, path1, path2):
        """두 번째 문서 선택 시 호출: 아래쪽 박스 채우기 + 유사도 계산"""
        name1 = os.path.basename(path1)
        name2 = os.path.basename(path2)
        
        self.info_label.setText("📊 문서 비교 분석 중...")
        QApplication.processEvents()
        
        try:
            # 텍스트 추출 (비교를 위해 넉넉하게 추출)
            t1 = app_logic.extract_text_from_file(path1, max_chars=50000)
            t2 = app_logic.extract_text_from_file(path2, max_chars=50000)
            
            # 유사도 계산
            score = app_logic.calculate_text_similarity(t1, t2)
            
            # === 1. 중앙 안내창에 유사도 표시 ===
            self.info_label.setText(f"<b>문서 비교 결과</b><br><br>📊 유사도: {score:.1f}%")
            self.info_label.setStyleSheet("padding: 15px; font-size: 11pt; background: #E8F4F8; border-radius: 8px; color: #012433;")
            self.info_label.setAlignment(Qt.AlignCenter)
            
            # === 2. 아래쪽 박스 (두 번째 문서 내용) ===
            self.doc_preview_bottom.setText(f"📄 파일명: {name2}\n{'='*40}\n\n{t2[:1500]}")
            
        except Exception as e:
            self.info_label.setText(f"❌ 오류 발생: {str(e)}")
            self.info_label.setStyleSheet("color: red; border: 2px solid red;")

    def extract_video_thumbnail(self, video_path):
        """비디오에서 첫 프레임을 추출하여 QPixmap으로 반환"""
        try:
            import cv2
            import numpy as np
            from PyQt5.QtGui import QImage
            
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                # BGR to RGB 변환
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame_rgb.shape
                bytes_per_line = 3 * width
                
                # QImage로 변환
                q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                # QPixmap으로 변환
                pixmap = QPixmap.fromImage(q_image)
                return pixmap
            else:
                return None
        except Exception as e:
            print(f"써네일 추출 오류: {e}")
            return None

    def show_video_info(self, video_path):
        """비디오 썸네일 표시"""
        filename = os.path.basename(video_path)
        try:
            # 비디오 썸네일 추출
            thumbnail = self.extract_video_thumbnail(video_path)
            
            if thumbnail and not thumbnail.isNull():
                # 썸네일 표시
                scaled = thumbnail.scaled(self.video_preview_top.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_preview_top.setPixmap(scaled)
                self.video_preview_top.setText("")  # 텍스트 제거
                self.video_preview_top.setToolTip(f"🎬 {filename}\n{video_path}")
                self.video_preview_top.setStyleSheet(
                    "border: 3px solid #00A9FF; background: #E8E8E8; padding: 5px;"
                )
                self.video_preview_top.setAlignment(Qt.AlignCenter)
            else:
                # 썸네일 추출 실패 시 텍스트로 표시
                file_size = os.path.getsize(video_path)
                size_str = app_logic.format_bytes(file_size)
                info_text = f"🎬 {filename}\n\n파일 크기: {size_str}\n\n(썸네일 로드 실패)"
                self.video_preview_top.setText(info_text)
                self.video_preview_top.setStyleSheet(
                    "border: 3px solid #00A9FF; background: #FFFFFF; "
                    "padding: 15px; font-size: 10pt; color: #012433;"
                )
            
            # 두 번째 영역은 안내 메시지
            self.video_preview_bottom.clear()
            self.video_preview_bottom.setPixmap(QPixmap())
            self.video_preview_bottom.setText("두 번째 비디오를 더블클릭하세요.")
            self.video_preview_bottom.setStyleSheet(
                "border: 3px solid #89CFF3; background: #E8E8E8; "
                "padding: 10px; font-size: 10pt; color: #555;"
            )
            
        except Exception as e:
            self.video_preview_top.setText(f"비디오 로드 오류: {str(e)}")

    def compare_videos(self, video1, video2):
        """두 비디오 비교"""
        name1 = os.path.basename(video1)
        name2 = os.path.basename(video2)
        
        self.info_label.setText("📊 비디오 비교 분석 중...")
        QApplication.processEvents()
        
        try:
            # 비디오 핑거프린트 추출
            hashes1 = app_logic.extract_video_fingerprint(video1)
            hashes2 = app_logic.extract_video_fingerprint(video2)
            
            if hashes1 is None or hashes2 is None:
                self.info_label.setText("⚠️ 비디오를 읽을 수 없거나 너무 짧습니다.")
                return
            
            # 유사도 계산
            similarity = app_logic.calculate_video_similarity(hashes1, hashes2)
            
            # === 1. 중앙 영역에 유사도 표시 ===
            self.info_label.setText(f"<b>비디오 비교 결과</b><br><br>📊 유사도: {similarity:.1f}%")
            self.info_label.setStyleSheet("padding: 15px; font-size: 11pt; background: #E8F4F8; border-radius: 8px; color: #012433;")
            self.info_label.setAlignment(Qt.AlignCenter)
            
            # === 2. 두 번째 비디오 썸네일 표시 ===
            thumbnail2 = self.extract_video_thumbnail(video2)
            
            if thumbnail2 and not thumbnail2.isNull():
                scaled2 = thumbnail2.scaled(self.video_preview_bottom.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_preview_bottom.setPixmap(scaled2)
                self.video_preview_bottom.setText("")  # 텍스트 제거
                self.video_preview_bottom.setToolTip(f"🎬 {name2}\n{video2}")
                self.video_preview_bottom.setStyleSheet(
                    "border: 3px solid #89CFF3; background: #E8E8E8; padding: 5px;"
                )
                self.video_preview_bottom.setAlignment(Qt.AlignCenter)
            else:
                # 썸네일 추출 실패 시 텍스트로 표시
                file_size2 = os.path.getsize(video2)
                size_str2 = app_logic.format_bytes(file_size2)
                info_text2 = f"🎬 {name2}\n\n파일 크기: {size_str2}\n\n(썸네일 로드 실패)"
                self.video_preview_bottom.setText(info_text2)
                self.video_preview_bottom.setStyleSheet(
                    "border: 3px solid #89CFF3; background: #FFFFFF; "
                    "padding: 15px; font-size: 10pt; color: #012433;"
                )
            
        except Exception as e:
            self.info_label.setText(f"❌ 오류 발생: {str(e)}")
            self.info_label.setStyleSheet("color: red; border: 2px solid red;")

    def show_quality_image_detail(self, img_path, result):
        """이미지 품질 검사 결과 상세 표시"""
        try:
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_preview_top.setPixmap(scaled)
                self.img_preview_top.setText("")
            else:
                self.img_preview_top.setText(f"이미지 로드 실패:\n{os.path.basename(img_path)}")

            score_data = result.get('score_data', {})
            final_score = score_data.get('final_score', 0)
            technical = score_data.get('technical', 0)
            aesthetic = score_data.get('aesthetic', 0)
            raw_metrics = score_data.get('raw_metrics', {})
            laplacian = raw_metrics.get('raw_laplacian', 0)
            brisque = raw_metrics.get('raw_brisque', 0)
            brightness = raw_metrics.get('raw_brightness', 0)
            penalty = score_data.get('penalty_applied', False)

            detail_text = f"""
📊 이미지 품질 분석 결과

파일명: {os.path.basename(img_path)}

━━━━━━━━━━━━━━━━━━━━━━
🏆 최종 점수: {final_score:.2f} / 100

━━━━━━━━━━━━━━━━━━━━━━
📈 세부 점수:
  • 기술 점수: {technical:.2f}
  • 미적 점수: {aesthetic:.2f}

━━━━━━━━━━━━━━━━━━━━━━
🔍 원본 지표:
  • Laplacian (선명도): {laplacian:.1f}
  • BRISQUE (품질): {brisque:.1f}
  • 밝기: {brightness:.1f}

━━━━━━━━━━━━━━━━━━━━━━
⚠️ 페널티: {"적용됨 (밝기 범위 벗어남)" if penalty else "없음"}
            """

            self.img_preview_bottom.clear()
            self.img_preview_bottom.setPixmap(QPixmap())
            self.img_preview_bottom.setText(detail_text.strip())
            self.img_preview_bottom.setStyleSheet(
                "border: 2px solid #00A9FF; background: #F5F5F5; "
                "padding: 15px; font-size: 10pt; color: #012433; text-align: left;"
            )
            self.img_preview_bottom.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        except Exception as e:
            self.img_preview_top.setText(f"오류: {str(e)}")
            self.img_preview_bottom.setText("")


# --- Matplotlib 캔버스 위젯 (UI 클래스) (변경 없음) ---
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Bright 테마로 설정
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#F5FBFF')
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

# --- 통계 패널 위젯 (UI 클래스) (변경 없음) ---
class StatisticsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #F5FBFF; border-radius: 4px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.stats_label = QLabel("스캔할 폴더를 드래그하세요.")
        self.stats_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("padding: 10px; font-size: 10pt; background-color: #FFFFFF; color: #012433; border-radius: 4px;")
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

    def showEvent(self, event):
        """페이지가 표시될 때 MainWindow의 dropped_files를 자동으로 처리"""
        super().showEvent(event)
        main_window = self.controller.parent()
        if main_window and hasattr(main_window, 'folder_path') and main_window.folder_path:
            if os.path.isdir(main_window.folder_path):
                # 자동으로 스캔 시작
                QApplication.processEvents()
                self.info_label.setText(f"'{os.path.basename(main_window.folder_path)}' 스캔 중...")
                QApplication.processEvents()
                duplicates, total_files, total_size = app_logic.find_duplicate_files(main_window.folder_path)
                self.process_statistics(duplicates, total_files, total_size)
                self.populate_table(duplicates)
                if not duplicates:
                    self.info_label.setText("✅ 스캔 완료: 중복 파일이 없습니다.")
                else:
                    self.info_label.setText(f"✅ 스캔 완료: {len(duplicates)}개 그룹의 중복 발견")

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
            self.info_label.setStyleSheet("border-color: #0078D7; color: #012433;")
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
        self.preview_label_top.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.preview_label_bottom = QLabel("파일 2를 드롭하세요")
        self.preview_label_bottom.setAlignment(Qt.AlignCenter)
        self.preview_label_bottom.setObjectName("ImagePreview")
        self.preview_label_bottom.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        preview_layout.addWidget(self.preview_label_top, 1)
        preview_layout.addWidget(self.preview_label_bottom, 1)
        self.single_panel_preview_widget = QWidget()
        single_preview_layout = QVBoxLayout(self.single_panel_preview_widget)
        single_preview_layout.setContentsMargins(0,0,0,0)
        self.single_preview_label = QLabel("테이블에서 이미지를 클릭하세요.")
        self.single_preview_label.setAlignment(Qt.AlignCenter)
        self.single_preview_label.setObjectName("ImagePreview")
        self.single_preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
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
    def showEvent(self, event):
        """페이지가 표시될 때 MainWindow의 dropped_files를 자동으로 처리"""
        super().showEvent(event)
        main_window = self.controller.parent()
        if main_window and hasattr(main_window, 'folder_path') and main_window.folder_path:
            if os.path.isdir(main_window.folder_path):
                # 폴더 스캔
                self.handle_folder_scan(main_window.folder_path)
            elif hasattr(main_window, 'dropped_files') and len(main_window.dropped_files) > 1:
                # 다중 파일 스캔
                self.handle_multiple_file_scan(main_window.dropped_files)

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
            self.info_label.setStyleSheet("border-color: #0078D7; color: #012433;")
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
    # [수정됨] app_ui.py 내부 SimilarVideoScanPage 클래스

    def handle_1v1_comparison(self, file1, file2):
        self.info_label.setText(f"분석 중...\n{os.path.basename(file1)}\nvs\n{os.path.basename(file2)}")
        QApplication.processEvents() # UI 멈춤 방지
        
        try:
            hashes1 = app_logic.extract_video_fingerprint(file1)
            hashes2 = app_logic.extract_video_fingerprint(file2)
            
            if hashes1 is None or hashes2 is None:
                self.info_label.setText("⚠️ 비디오를 읽을 수 없거나 너무 짧습니다.")
                return

            similarity = app_logic.calculate_video_similarity(hashes1, hashes2)
            
            # --- [수정 1] 드롭존(info_label)에 표시할 텍스트 스타일 개선 ---
            result_text = (f"<b>🎬 1:1 비디오 비교 결과</b><br><br>"
                           f"<b>파일 1:</b> {os.path.basename(file1)}<br>"
                           f"<b>파일 2:</b> {os.path.basename(file2)}<br><br>"
                           f"📊 유사도: <font size='+2' color='#0078D7'><b>{similarity:.1f}%</b></font>")
            
            self.info_label.setText(result_text)
            self.info_label.setAlignment(Qt.AlignCenter)
            self.info_label.setStyleSheet("padding: 20px; font-size: 11pt; background: #E8F4F8; border: 3px solid #00A9FF; border-radius: 8px; color: #012433;")
            
            # --- [수정 2] 테이블에도 결과 데이터 추가 (이미지 페이지와 동작 통일) ---
            # 그룹 데이터 형식: [(경로1, 100.0), (경로2, 유사도)]
            group_data = [(file1, 100.0), (file2, similarity)]
            # populate_table은 그룹의 리스트를 받으므로 []로 한 번 더 감쌈
            self.populate_table([group_data])
            
        except AttributeError:
            self.info_label.setText("❌ 오류: app_logic.py에 비디오 처리 함수가 없습니다.")
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
        # [수정] 체크박스를 위한 열 1개 추가 (총 7개 열)
        self.result_table.setColumnCount(7) 
        
        # 테이블 헤더 정의
        self.result_table.setHorizontalHeaderLabels([
            "선택", "파일 경로", "종합 점수", "미적 점수", "기술 점수", "선명도", "화질"
        ])

        # '선택' 열 너비 고정
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.result_table.setColumnWidth(0, 50)
        
        # 나머지 열 설정
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # 파일 경로
        for i in range(2, 7):
            self.result_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        
        # [추가] 테이블 셀 클릭 이벤트 연결
        self.result_table.cellClicked.connect(self.show_image_on_click)

        left_layout.addWidget(self.info_label, 1)
        left_layout.addWidget(self.result_table, 3)
        
        # 2. 오른쪽: Best Shot 미리보기와 통계/제어 버튼
        right_layout = QVBoxLayout()
        
        # Best Shot 미리보기 패널 (ImagePreview)
        self.best_shot_image = QLabel("검사할 이미지 파일을 포함한 폴더를 드롭하세요.")
        self.best_shot_image.setStyleSheet("padding: 10px; background-color: #E8E8E8; border-radius: 4px; min-height: 200px; color: #012433;")
        self.best_shot_image.setAlignment(Qt.AlignCenter)
        self.best_shot_image.setObjectName("ImagePreview")
        self.best_shot_image.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        # 1위 이미지 통계 텍스트 전용 패널
        self.best_shot_stats = QLabel("")
        self.best_shot_stats.setStyleSheet("padding: 10px; background-color: #FFFFFF; border: 1px solid #CDF5FD; border-radius: 4px; max-height: 150px; color: #012433;")
        self.best_shot_stats.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.best_shot_stats.setWordWrap(True)
        
        self.canvas = None # Matplotlib 캔버스 제거
        
        right_layout.addWidget(self.best_shot_image, 1) # 미리보기/통계 패널
        right_layout.addWidget(self.best_shot_stats, 0) # 통계 텍스트
        
        # 선택한 파일 삭제 버튼
        self.batch_delete_btn = QPushButton("선택한 파일 삭제")
        self.batch_delete_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_TrashIcon))
        self.batch_delete_btn.setStyleSheet("background-color: #7A3A3A;")
        self.batch_delete_btn.clicked.connect(self.handle_batch_delete)
        right_layout.addWidget(self.batch_delete_btn)

        button_layout = QHBoxLayout()
        reset_btn = QPushButton("다시 하기")
        reset_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        reset_btn.clicked.connect(self.reset_page)
        back_btn = QPushButton("뒤로 가기")
        back_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowBack))
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))
        
        button_layout.addStretch(1)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(back_btn)
        
        right_layout.addLayout(button_layout)
        
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)
        
    def showEvent(self, event):
        """페이지가 표시될 때 MainWindow의 dropped_files를 자동으로 처리"""
        super().showEvent(event)
        main_window = self.controller.parent()
        if main_window and hasattr(main_window, 'folder_path') and main_window.folder_path:
            if os.path.isdir(main_window.folder_path):
                # 자동으로 품질 검사 시작
                self.info_label.setText(f"'{os.path.basename(main_window.folder_path)}' 이미지 품질 분석 중...")
                QApplication.processEvents()
                results, success = app_logic.analyze_image_quality_in_folder(main_window.folder_path)
                if success and results:
                    self.populate_table(results)
                    self.info_label.setText(f"✅ 분석 완료: {len(results)}개 이미지")
                else:
                    self.info_label.setText("⚠️ 이미지를 찾을 수 없거나 분석에 실패했습니다.")

    def reset_page(self):
        self.info_label.setText("\n\n이미지 품질을 검사할 폴더를\n이곳으로 드래그 앤 드롭하세요.\n\n")
        self.info_label.setStyleSheet("")
        self.result_table.setRowCount(0)
        self.best_shot_image.setText("검사할 이미지 파일을 포함한 폴더를 드롭하세요.") 
        self.best_shot_image.clear() 
        self.best_shot_stats.setText("")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
            self.info_label.setStyleSheet("border-color: #0078D7; color: #012433;")
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return
        folder_path = files[0]

        if os.path.isdir(folder_path):
            self.info_label.setText(f"'{os.path.basename(folder_path)}' 폴더 내 이미지 품질 분석 중... (시간 소요)")
            QApplication.processEvents()
            
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

    def handle_batch_delete(self):
        files_to_delete = []
        for row in range(self.result_table.rowCount()):
            cell_widget = self.result_table.cellWidget(row, 0)
            if cell_widget:
                chk_box = cell_widget.findChild(QCheckBox)
                if chk_box and chk_box.isChecked():
                    files_to_delete.append({
                        "row": row,
                        "path": chk_box.property("file_path"),
                        "size": chk_box.property("file_size")
                    })

        if not files_to_delete:
            QMessageBox.information(self, "선택 없음", "삭제할 파일을 하나 이상 선택하세요.")
            return

        total_size_to_delete = sum(item['size'] for item in files_to_delete) 

        reply = QMessageBox.question(self, '일괄 삭제 확인',
                                     f"정말로 <b>{len(files_to_delete)}개</b>의 파일을 영구적으로 삭제하시겠습니까?<br><br>"
                                     f"<b><font color='#FF6347'>총 확보 용량: {app_logic.format_bytes(total_size_to_delete)}</font></b><br><br>"
                                     f"이 작업은 되돌릴 수 없습니다.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        deleted_count = 0
        space_saved = 0
        
        for item in sorted(files_to_delete, key=lambda x: x['row'], reverse=True):
            try:
                os.remove(item['path'])
                self.result_table.removeRow(item['row'])
                deleted_count += 1
                space_saved += item['size'] 
            except Exception as e:
                print(f"파일 삭제 오류 ({item['path']}): {e}")

        if deleted_count > 0:
            QMessageBox.information(self, "삭제 완료",
                                    f"총 {deleted_count}개의 파일을 삭제했습니다.\n"
                                    f"확보된 용량: {app_logic.format_bytes(space_saved)}")
        else:
            QMessageBox.warning(self, "삭제 실패", "파일을 삭제하는 중 오류가 발생했습니다.")

    def display_best_shot_preview(self, file_path):
        """지정된 파일 경로의 이미지를 미리보기 패널에 표시합니다."""
        label = self.best_shot_image
        if os.path.exists(file_path):
            try:
                pixmap = QPixmap()
                with open(file_path, 'rb') as f:
                    img_bytes = f.read()
                pixmap.loadFromData(img_bytes)
                
                label.setPixmap(pixmap.scaled(label.size(), 
                                              Qt.KeepAspectRatio, 
                                              Qt.SmoothTransformation))
                label.setText("") 
                
            except Exception as e:
                label.setText(f"미리보기 오류:\n{os.path.basename(file_path)}\n{e}")
        else:
            label.setText("파일을 찾을 수 없습니다.")

    # [추가] 통계 텍스트 업데이트 함수 (클릭 이벤트 처리 시 사용)
    def update_stats_panel(self, data):
        """주어진 이미지 데이터로 통계 텍스트 패널을 업데이트합니다."""
        if not data:
            self.best_shot_stats.setText("")
            return

        best_score = data['score_data']['final_score']
        best_tech = data['score_data']['technical']
        best_aes = data['score_data']['aesthetic']
        best_lap = data['score_data']['raw_metrics']['raw_laplacian']
        
        info_text = (
            f"<b>🥇 파일: {os.path.basename(data['path'])}</b><br>"
            f"<span style='font-size: 16pt; color: #FFD700;'>{best_score:.2f}</span> / 100<br>"
            f"<hr style='border: 1px solid #444; margin-top: 5px; margin-bottom: 5px;'>"
            f"미적 점수: {best_aes:.2f}<br>"
            f"기술 점수: {best_tech:.2f}<br>"
            f"<small>(Laplacian: {best_lap:.0f})</small>"
        )
        self.best_shot_stats.setText(info_text)

    # [수정] Top 3 클릭 시 미리보기와 텍스트를 연동하는 함수
    def show_image_on_click(self, row, column):
        """테이블 클릭 시 선택한 이미지를 미리보기 패널에 표시하고 통계 텍스트를 업데이트합니다."""
        
        item = self.result_table.item(row, 1) # 1열은 파일 경로 아이템
        
        if not item: return

        # 저장해둔 전체 데이터 가져오기
        full_data = item.data(Qt.UserRole + 1) 
        file_path = item.text()

        # 데이터가 있다면 순위 상관없이 표시
        if full_data:
            self.display_best_shot_preview(file_path) # 미리보기 이미지 업데이트
            self.update_stats_panel(full_data)
            

    def resizeEvent(self, event):
        """QLabel 크기 변경 시 이미지도 다시 조정"""
        super().resizeEvent(event)
        if self.best_shot_image.pixmap() and not self.best_shot_image.text():
            pixmap = self.best_shot_image.pixmap()
            self.best_shot_image.setPixmap(pixmap.scaled(self.best_shot_image.size(), 
                                                           Qt.KeepAspectRatio, 
                                                           Qt.SmoothTransformation))

    # [수정] populate_table 함수 (체크박스 및 Top 3 데이터 저장 로직 수정)
    def populate_table(self, results):
        self.result_table.setRowCount(0)
        
        for rank, data in enumerate(results):
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            
            # 파일 경로 및 크기 (삭제 로직 사용을 위해 필요)
            path_item = QTableWidgetItem(data['path'])
            file_size = data.get('size', 0) 
            
            # 점수 항목들
            final_score_item = QTableWidgetItem(f"{data['score_data']['final_score']:.2f}")
            aes_item = QTableWidgetItem(f"{data['score_data']['aesthetic']:.2f}")
            tech_item = QTableWidgetItem(f"{data['score_data']['technical']:.2f}")
            lap_item = QTableWidgetItem(f"{data['score_data']['raw_metrics']['raw_laplacian']:.0f}")
            brisque_item = QTableWidgetItem(f"{data['score_data']['raw_metrics']['raw_brisque']:.0f}")

            # 체크박스 위젯 생성 및 정보 저장
            checkbox_widget = QWidget()
            chk_layout = QHBoxLayout(checkbox_widget)
            chk_box = QCheckBox()
            chk_layout.addWidget(chk_box)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0,0,0,0)
            checkbox_widget.setLayout(chk_layout)
            
            chk_box.setProperty("file_path", data['path'])
            chk_box.setProperty("file_size", file_size) 
            chk_box.setProperty("table_row", row_position)
            
            # 1~3위 강조 및 데이터 저장
            current_rank = rank + 1
            
            # 1. 모든 행에 데이터 저장 (그래야 클릭 시 정보를 가져올 수 있음)
            path_item.setData(Qt.UserRole, current_rank) 
            path_item.setData(Qt.UserRole + 1, data) 

            # 2. 1~3위만 색상 강조 (기능 제한은 풀고, 스타일만 유지)
            if current_rank <= 3:
                 color = QColor("#FFD700") if current_rank == 1 else (QColor("#C0C0C0") if current_rank == 2 else QColor("#CD7F32"))
                 path_item.setForeground(color)
                 final_score_item.setForeground(color)
                 final_score_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            # --- [수정된 부분 끝] ---

            self.result_table.setCellWidget(row_position, 0, checkbox_widget)
            self.result_table.setItem(row_position, 1, path_item)
            self.result_table.setItem(row_position, 2, final_score_item)
            self.result_table.setItem(row_position, 3, aes_item)
            self.result_table.setItem(row_position, 4, tech_item)
            self.result_table.setItem(row_position, 5, lap_item)
            self.result_table.setItem(row_position, 6, brisque_item)
            
            for i in range(2, 7): 
                 item = self.result_table.item(row_position, i)
                 item.setTextAlignment(Qt.AlignCenter)
                 if current_rank == 1:
                     item.setBackground(QColor("#444430"))
        
        if results:
             best_shot_path = results[0]['path']
             self.display_best_shot_preview(best_shot_path)
             self.update_stats_panel(results[0])
        else:
             self.best_shot_stats.setText("")

# --- 비디오 유사도 검사 화면 (UI 클래스) ---
class SimilarVideoScanPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setAcceptDrops(True)
        self.first_file_path = None
        self.first_selected_video = None  # 첫 번째 선택된 비디오
        
        # 비디오 확장자 정의
        self.VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v')

        self.initial_text = ("\n\n비디오 유사도를 스캔할 폴더를 드롭하거나,\n"
                             "비교할 비디오 파일 2개를 하나씩 드롭하세요.\n\n")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- 왼쪽 레이아웃 (드롭존 + 결과 테이블) ---
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        self.info_label = QLabel(self.initial_text)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setMinimumHeight(150)

        # 슬라이더 (유사도 기준)
        slider_box = QFrame()
        slider_box.setFrameShape(QFrame.StyledPanel)
        slider_box.setStyleSheet("background-color: #3A3A3A; border-radius: 4px; padding: 10px;")
        slider_layout = QVBoxLayout(slider_box)
        
        self.threshold_label = QLabel("유사도 기준: 80% (높을수록 더 비슷해야 함)")
        self.threshold_label.setAlignment(Qt.AlignCenter)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(50, 100) # 비디오는 해시 변동이 크므로 범위를 넓게 잡음
        self.threshold_slider.setValue(80)
        self.threshold_slider.valueChanged.connect(self.update_slider_label)
        
        slider_layout.addWidget(self.threshold_label)
        slider_layout.addWidget(self.threshold_slider)

        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setObjectName("ResultTable")
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["파일 경로", "유사도"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.cellDoubleClicked.connect(self.on_video_double_clicked)  # 더블클릭 연결
        
        left_layout.addWidget(self.info_label, 1)
        left_layout.addWidget(slider_box)
        left_layout.addWidget(self.result_table, 3)

        # --- 오른쪽 레이아웃 (비디오 미리보기 2개) ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        # 첫 번째 비디오 미리보기
        video_top_label = QLabel("🔷 첫 번째 비디오")
        video_top_label.setStyleSheet("font-weight: bold; color: #00A9FF; font-size: 10pt;")
        self.video_preview_top = QLabel("첫 번째 비디오를 더블클릭하세요.")
        self.video_preview_top.setAlignment(Qt.AlignCenter)
        self.video_preview_top.setStyleSheet("border: 3px solid #00A9FF; background: #E8E8E8; padding: 10px; font-size: 10pt; color: #555;")
        self.video_preview_top.setMinimumHeight(150)
        
        # 두 번째 비디오 미리보기
        video_bottom_label = QLabel("🔷 두 번째 비디오")
        video_bottom_label.setStyleSheet("font-weight: bold; color: #89CFF3; font-size: 10pt;")
        self.video_preview_bottom = QLabel("두 번째 비디오를 더블클릭하세요.")
        self.video_preview_bottom.setAlignment(Qt.AlignCenter)
        self.video_preview_bottom.setStyleSheet("border: 3px solid #89CFF3; background: #E8E8E8; padding: 10px; font-size: 10pt; color: #555;")
        self.video_preview_bottom.setMinimumHeight(150)

        reset_btn = QPushButton("다시 하기")
        reset_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        reset_btn.clicked.connect(self.reset_page)

        back_btn = QPushButton("뒤로 가기")
        back_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowBack))
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))

        right_layout.addWidget(video_top_label)
        right_layout.addWidget(self.video_preview_top, 1)
        right_layout.addWidget(video_bottom_label)
        right_layout.addWidget(self.video_preview_bottom, 1)
        right_layout.addWidget(reset_btn)
        right_layout.addWidget(back_btn)

        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)

    def showEvent(self, event):
        """페이지가 표시될 때 MainWindow의 dropped_files를 자동으로 처리"""
        super().showEvent(event)
        main_window = self.controller.parent()
        if main_window and hasattr(main_window, 'folder_path') and main_window.folder_path:
            if os.path.isdir(main_window.folder_path):
                # 폴더 스캔
                self.handle_folder_scan(main_window.folder_path)
            elif hasattr(main_window, 'dropped_files') and len(main_window.dropped_files) > 1:
                # 다중 파일 스캔
                self.handle_multiple_file_scan(main_window.dropped_files)

    def update_slider_label(self, value):
        self.threshold_label.setText(f"유사도 기준: {value}% (높을수록 더 비슷해야 함)")

    def reset_page(self):
        self.first_file_path = None
        self.info_label.setText(self.initial_text)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setStyleSheet("")
        self.result_table.setRowCount(0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
            self.info_label.setStyleSheet("border-color: #0078D7; color: #012433;")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if self.first_file_path is None:
            self.reset_page()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return
        
        # 초기화
        self.result_table.setRowCount(0)
        
        # 1. 폴더가 포함된 경우 (폴더 통째로 스캔)
        if len(files) == 1 and os.path.isdir(files[0]):
            self.first_file_path = None
            self.handle_folder_scan(files[0])
            return
            
        # 2. 파일들만 있는 경우
        # 비디오 파일인지 검증
        valid_videos = [f for f in files if f.lower().endswith(self.VIDEO_EXTENSIONS)]
        
        if len(valid_videos) != len(files):
            self.info_label.setText("⚠️ 지원하지 않는 파일이 섞여 있습니다.\n비디오 파일(mp4, avi 등)만 드롭하세요.")
            self.info_label.setStyleSheet("border: 2px solid red;")
            return

        if not valid_videos:
            self.reset_page()
            return

        # 3. 시나리오 분기 (다중 파일 스캔 vs 1:1 비교)
        if len(valid_videos) > 1:
            # 여러 파일을 한꺼번에 드롭 -> 상호 비교
            self.first_file_path = None
            self.handle_multiple_file_scan(valid_videos)
            
        elif len(valid_videos) == 1:
            dropped_file = valid_videos[0]
            
            if self.first_file_path is None:
                # 첫 번째 파일 등록
                self.first_file_path = dropped_file
                filename = os.path.basename(dropped_file)
                self.info_label.setText(f"✅ <b>첫 번째 비디오 선택 완료</b><br><br>🎬 {filename}<br><br>━━━━━━━━━━━━━━━━━━━━<br><br>두 번째 비디오를 드롭하세요")
                self.info_label.setAlignment(Qt.AlignCenter)
                self.info_label.setStyleSheet("padding: 20px; background: #E8F4F8; border: 3px solid #00A9FF; border-radius: 8px; color: #012433; font-size: 11pt;")
            else:
                # 두 번째 파일 등록 -> 1:1 비교 실행
                self.handle_1v1_comparison(self.first_file_path, dropped_file)
                self.first_file_path = None # 비교 후 초기화

    # --- 로직 처리 헬퍼 함수들 ---
    
    def handle_1v1_comparison(self, file1, file2):
        self.info_label.setText(f"분석 중...\n{os.path.basename(file1)}\nvs\n{os.path.basename(file2)}")
        QApplication.processEvents() # UI 멈춤 방지
        
        # app_logic에 이 함수들이 구현되어 있어야 합니다.
        try:
            hashes1 = app_logic.extract_video_fingerprint(file1)
            hashes2 = app_logic.extract_video_fingerprint(file2)
            
            if hashes1 is None or hashes2 is None:
                self.info_label.setText("⚠️ 비디오를 읽을 수 없거나 너무 짧습니다.")
                return

            similarity = app_logic.calculate_video_similarity(hashes1, hashes2)
            
            result_text = (f"<b>비디오 비교 결과</b><br><br>"
                           f"<b>🎬 첫 번째:</b> {os.path.basename(file1)}<br>"
                           f"<b>🎬 두 번째:</b> {os.path.basename(file2)}<br><br>"
                           f"<b>📊 유사도: <font size='+2' color='#0078D7'>{similarity:.1f}%</font></b>")
            
            self.info_label.setText(result_text)
            self.info_label.setAlignment(Qt.AlignCenter)
            self.info_label.setStyleSheet("padding: 15px; font-size: 11pt; background: #E8F4F8; border-radius: 8px; color: #012433;")
            
        except AttributeError:
            self.info_label.setText("❌ 오류: app_logic.py에 비디오 처리 함수가 없습니다.")

    def handle_folder_scan(self, folder_path):
        self.info_label.setText(f"'{os.path.basename(folder_path)}' 폴더 내부 비디오 스캔 중...\n(시간이 오래 걸릴 수 있습니다)")
        QApplication.processEvents()
        
        try:
            # app_logic.find_similar_videos_from_folder 구현 필요
            threshold = self.threshold_slider.value()
            similar_groups = app_logic.find_similar_videos_from_folder(folder_path, threshold)
            
            self.populate_table(similar_groups)
            
            if not similar_groups:
                self.info_label.setText("✅ 스캔 완료: 유사한 비디오가 없습니다.")
            else:
                self.info_label.setText(f"검색 완료. 총 {len(similar_groups)}개의 유사 그룹 발견.")
        except AttributeError:
            self.info_label.setText("❌ 오류: app_logic.py에 비디오 폴더 스캔 함수가 없습니다.")

    def handle_multiple_file_scan(self, file_list):
        self.info_label.setText(f"총 {len(file_list)}개 비디오 파일 상호 비교 중...")
        QApplication.processEvents()
        
        try:
            # app_logic.find_similar_videos_from_list 구현 필요
            threshold = self.threshold_slider.value()
            similar_groups = app_logic.find_similar_videos_from_list(file_list, threshold)
            
            self.populate_table(similar_groups)
            
            if not similar_groups:
                self.info_label.setText("✅ 스캔 완료: 유사한 비디오가 없습니다.")
            else:
                self.info_label.setText(f"검색 완료. 총 {len(similar_groups)}개의 유사 그룹 발견.")
        except AttributeError:
            self.info_label.setText("❌ 오류: app_logic.py에 비디오 리스트 스캔 함수가 없습니다.")

    def populate_table(self, groups):
        self.result_table.setRowCount(0)
        for i, group in enumerate(groups):
            row_position = self.result_table.rowCount()
            self.result_table.insertRow(row_position)
            
            # 그룹 헤더
            header_item = QTableWidgetItem(f"🎬 비디오 그룹 {i+1} (총 {len(group)}개)")
            header_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            header_item.setBackground(QColor("#5A3A3A")) # 비디오는 붉은 계열로 구분
            self.result_table.setSpan(row_position, 0, 1, 2)
            self.result_table.setItem(row_position, 0, header_item)
            
            # 그룹 내 파일들
            for path, similarity in group:
                row_position = self.result_table.rowCount()
                self.result_table.insertRow(row_position)
                
                path_item = QTableWidgetItem(path)
                path_item.setToolTip(path)
                
                if similarity == 100.0:
                    score_item = QTableWidgetItem("기준 (100%)")
                    score_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                else:
                    score_item = QTableWidgetItem(f"{similarity:.1f}%")
                
                self.result_table.setItem(row_position, 0, path_item)
                self.result_table.setItem(row_position, 1, score_item)

    def on_video_double_clicked(self, row, column):
        """비디오 테이블 더블클릭 시 호출"""
        # 헤더 행은 무시
        item = self.result_table.item(row, 0)
        if not item or self.result_table.columnSpan(row, 0) > 1:
            return
        
        clicked_path = item.text()
        if not clicked_path or not os.path.isfile(clicked_path):
            return
        
        if not self.first_selected_video:
            # 첫 번째 비디오 선택
            self.first_selected_video = clicked_path
            self.show_video_info(clicked_path, is_first=True)
        else:
            # 두 번째 비디오 선택 - 비교 실행
            self.compare_videos(self.first_selected_video, clicked_path)
            self.first_selected_video = None  # 초기화

    def extract_video_thumbnail(self, video_path):
        """비디오에서 첫 프레임을 추출하여 QPixmap으로 반환"""
        try:
            import cv2
            import numpy as np
            from PyQt5.QtGui import QImage
            
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                # BGR to RGB 변환
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame_rgb.shape
                bytes_per_line = 3 * width
                
                # QImage로 변환
                q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                # QPixmap으로 변환
                pixmap = QPixmap.fromImage(q_image)
                return pixmap
            else:
                return None
        except Exception as e:
            print(f"썸네일 추출 오류: {e}")
            return None

    def show_video_info(self, video_path, is_first=True):
        """비디오 썸네일 표시"""
        filename = os.path.basename(video_path)
        try:
            # 비디오 썸네일 추출
            thumbnail = self.extract_video_thumbnail(video_path)
            
            if thumbnail and not thumbnail.isNull():
                # 썸네일 표시
                scaled = thumbnail.scaled(self.video_preview_top.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_preview_top.setPixmap(scaled)
                self.video_preview_top.setText("")  # 텍스트 제거
                self.video_preview_top.setToolTip(f"🎬 {filename}\n{video_path}")
                self.video_preview_top.setStyleSheet(
                    "border: 3px solid #00A9FF; background: #E8E8E8; padding: 5px;"
                )
                self.video_preview_top.setAlignment(Qt.AlignCenter)
            else:
                # 썸네일 추출 실패 시 텍스트로 표시
                file_size = os.path.getsize(video_path)
                size_str = app_logic.format_bytes(file_size)
                info_text = f"🎬 {filename}\n\n파일 크기: {size_str}\n\n(썸네일 로드 실패)"
                self.video_preview_top.setText(info_text)
                self.video_preview_top.setStyleSheet(
                    "border: 3px solid #00A9FF; background: #FFFFFF; "
                    "padding: 15px; font-size: 10pt; color: #012433;"
                )
            
            # 두 번째 영역은 안내 메시지
            self.video_preview_bottom.clear()
            self.video_preview_bottom.setPixmap(QPixmap())
            self.video_preview_bottom.setText("두 번째 비디오를 더블클릭하세요.")
            self.video_preview_bottom.setStyleSheet(
                "border: 3px solid #89CFF3; background: #E8E8E8; "
                "padding: 10px; font-size: 10pt; color: #555;"
            )
            
        except Exception as e:
            self.video_preview_top.setText(f"비디오 로드 오류: {str(e)}")

    def compare_videos(self, video1, video2):
        """두 비디오 비교"""
        name1 = os.path.basename(video1)
        name2 = os.path.basename(video2)
        
        self.info_label.setText("📊 비디오 비교 분석 중...")
        QApplication.processEvents()
        
        try:
            # 비디오 핑거프린트 추출
            hashes1 = app_logic.extract_video_fingerprint(video1)
            hashes2 = app_logic.extract_video_fingerprint(video2)
            
            if hashes1 is None or hashes2 is None:
                self.info_label.setText("⚠️ 비디오를 읽을 수 없거나 너무 짧습니다.")
                return
            
            # 유사도 계산
            similarity = app_logic.calculate_video_similarity(hashes1, hashes2)
            
            # === 1. 중앙 영역에 유사도 표시 ===
            self.info_label.setText(f"<b>비디오 비교 결과</b><br><br>📊 유사도: {similarity:.1f}%")
            self.info_label.setStyleSheet("padding: 15px; font-size: 11pt; background: #E8F4F8; border-radius: 8px; color: #012433;")
            self.info_label.setAlignment(Qt.AlignCenter)
            
            # === 2. 두 번째 비디오 썸네일 표시 ===
            thumbnail2 = self.extract_video_thumbnail(video2)
            
            if thumbnail2 and not thumbnail2.isNull():
                scaled2 = thumbnail2.scaled(self.video_preview_bottom.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_preview_bottom.setPixmap(scaled2)
                self.video_preview_bottom.setText("")  # 텍스트 제거
                self.video_preview_bottom.setToolTip(f"🎬 {name2}\n{video2}")
                self.video_preview_bottom.setStyleSheet(
                    "border: 3px solid #89CFF3; background: #E8E8E8; padding: 5px;"
                )
                self.video_preview_bottom.setAlignment(Qt.AlignCenter)
            else:
                # 썸네일 추출 실패 시 텍스트로 표시
                file_size2 = os.path.getsize(video2)
                size_str2 = app_logic.format_bytes(file_size2)
                info_text2 = f"🎬 {name2}\n\n파일 크기: {size_str2}\n\n(썸네일 로드 실패)"
                self.video_preview_bottom.setText(info_text2)
                self.video_preview_bottom.setStyleSheet(
                    "border: 3px solid #89CFF3; background: #FFFFFF; "
                    "padding: 15px; font-size: 10pt; color: #012433;"
                )
            
        except Exception as e:
            self.info_label.setText(f"❌ 오류 발생: {str(e)}")
            self.info_label.setStyleSheet("color: red; border: 2px solid red;")
                
                
# --- 문서 유사도 검사 화면 (UI 클래스) ---
class SimilarDocScanPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setAcceptDrops(True)
        self.first_file_path = None
        
        self.DOC_EXTENSIONS = (
            # 1. 일반 문서 및 메모
            '.txt', '.md', '.markdown', '.pdf', '.docx', '.rtf', '.odt', '.tex', '.bib', '.hwp',
            
            # 2. 데이터 시트, 로그, 설정 파일
            '.csv', '.tsv', '.log', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', 
            '.conf', '.cfg', '.env', '.properties', '.gradle', '.gitignore',
            
            # 3. 웹 개발 (HTML, CSS, JS 프레임워크 등)
            '.html', '.htm', '.xhtml', '.css', '.scss', '.less', '.sass',
            '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.json',
            '.php', '.asp', '.aspx', '.jsp', '.jspx',
            
            # 4. 주요 프로그래밍 언어 소스코드
            '.py', '.ipynb',          # Python (ipynb는 JSON 구조라 텍스트로 읽힘)
            '.c', '.cpp', '.h', '.hpp', # C/C++
            '.cs', '.java', '.kt', '.kts', # C#, Java, Kotlin
            '.swift', '.m', '.mm',    # iOS/Mac
            '.go', '.rs',             # Go, Rust
            '.rb', '.pl', '.pm',      # Ruby, Perl
            '.lua', '.r', '.dart', '.scala', '.erl', '.el',
            
            # 5. 쉘 스크립트 및 배치 파일
            '.sh', '.bash', '.zsh', '.bat', '.ps1', '.cmd', '.vbs',
            
            # 6. 데이터베이스 및 쿼리
            '.sql', '.sqlite',
            
            # 7. 기타 유용한 텍스트 포맷
            '.svg',                   # 벡터 이미지 (XML 텍스트 기반이므로 비교 가능)
            '.srt', '.vtt', '.smi',   # 자막 파일 (텍스트 비교 매우 유용)
            '.dockerfile', '.makefile' # 빌드 스크립트
        )

        self.initial_text = ("\n\n문서 유사도를 스캔할 폴더를 드롭하거나,\n"
                             "비교할 문서 파일 2개를 하나씩 드롭하세요.\n"
                             "(지원: txt, pdf, docx, md, py 등)\n\n")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 왼쪽: 설정 및 결과
        left_layout = QVBoxLayout()
        self.info_label = QLabel(self.initial_text)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setMinimumHeight(120)

        # 슬라이더
        slider_box = QFrame()
        slider_box.setStyleSheet("background-color: #3A3A3A; border-radius: 4px; padding: 10px;")
        slider_layout = QVBoxLayout(slider_box)
        self.threshold_label = QLabel("유사도 기준: 90% (높을수록 더 비슷해야 함)")
        self.threshold_label.setAlignment(Qt.AlignCenter)
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(50, 100)
        self.threshold_slider.setValue(90)
        self.threshold_slider.valueChanged.connect(self.update_slider_label)
        slider_layout.addWidget(self.threshold_label)
        slider_layout.addWidget(self.threshold_slider)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["파일 경로", "유사도"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # [수정] cellClicked 제거 - 더블클릭과 충돌 방지
        self.result_table.cellDoubleClicked.connect(self.on_doc_double_clicked) # 더블클릭 시 1:1 비교
        
        # 첫 번째 선택된 문서 추적용
        self.first_selected_doc = None
        self.first_doc_text = None  # 첫 번째 문서의 텍스트 저장

        left_layout.addWidget(self.info_label, 1)
        left_layout.addWidget(slider_box)
        left_layout.addWidget(self.result_table, 3)

        # 오른쪽: 텍스트 미리보기 패널 (2개 영역: 위/아래)
        right_layout = QVBoxLayout()
        
        # 첫 번째 문서 미리보기 (위쪽)
        self.text_preview_top = QTextEdit()
        self.text_preview_top.setReadOnly(True)
        self.text_preview_top.setPlaceholderText("📄 첫 번째 문서를 더블클릭하세요")
        self.text_preview_top.setStyleSheet("background-color: #FFFFFF; color: #012433; border: 3px solid #00A9FF; border-radius: 6px; padding: 10px;")
        
        # 두 번째 문서 미리보기 (아래쪽)
        self.text_preview_bottom = QTextEdit()
        self.text_preview_bottom.setReadOnly(True)
        self.text_preview_bottom.setPlaceholderText("📄 두 번째 문서를 더블클릭하세요")
        self.text_preview_bottom.setStyleSheet("background-color: #FFFFFF; color: #012433; border: 3px solid #89CFF3; border-radius: 6px; padding: 10px;")

        reset_btn = QPushButton("다시 하기")
        reset_btn.clicked.connect(self.reset_page)
        back_btn = QPushButton("뒤로 가기")
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))

        right_layout.addWidget(self.text_preview_top, 1)
        right_layout.addWidget(self.text_preview_bottom, 1)
        right_layout.addWidget(reset_btn)
        right_layout.addWidget(back_btn)

        main_layout.addLayout(left_layout, 3) # 비율 조정
        main_layout.addLayout(right_layout, 2)

    def showEvent(self, event):
        """페이지가 표시될 때 MainWindow의 dropped_files를 자동으로 처리"""
        super().showEvent(event)
        main_window = self.controller.parent()
        if main_window and hasattr(main_window, 'folder_path') and main_window.folder_path:
            if os.path.isdir(main_window.folder_path):
                # 폴더 스캔
                self.handle_folder_scan(main_window.folder_path)
            elif hasattr(main_window, 'dropped_files') and len(main_window.dropped_files) > 1:
                # 다중 파일 스캔
                self.handle_multiple_scan(main_window.dropped_files)

    def update_slider_label(self, value):
        self.threshold_label.setText(f"유사도 기준: {value}%")

    def reset_page(self):
        self.first_file_path = None
        self.first_selected_doc = None
        self.first_doc_text = None  # 캐시 초기화
        self.info_label.setText(self.initial_text)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("")
        self.result_table.setRowCount(0)
        self.text_preview_top.clear()
        self.text_preview_top.setPlaceholderText("📄 첫 번째 문서를 더블클릭하세요")
        self.text_preview_bottom.clear()
        self.text_preview_bottom.setPlaceholderText("📄 두 번째 문서를 더블클릭하세요")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
            self.info_label.setStyleSheet("border-color: #0078D7; color: #012433;")
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files: return
        self.result_table.setRowCount(0)
        
        # 1. 폴더 스캔
        if len(files) == 1 and os.path.isdir(files[0]):
            self.first_file_path = None
            self.handle_folder_scan(files[0])
            return
            
        # 2. 파일 필터링
        valid_docs = [f for f in files if f.lower().endswith(self.DOC_EXTENSIONS)]
        if not valid_docs:
            self.info_label.setText("⚠️ 지원하지 않는 문서 형식입니다.")
            return

        # 3. 다중 파일 또는 1:1 비교
        if len(valid_docs) > 1:
            self.first_file_path = None
            self.handle_multiple_scan(valid_docs)
        elif len(valid_docs) == 1:
            dropped = valid_docs[0]
            if self.first_file_path is None:
                self.first_file_path = dropped
                filename = os.path.basename(dropped)
                self.info_label.setText(f"✅ <b>첫 번째 문서 선택 완료</b><br><br>📄 {filename}<br><br>━━━━━━━━━━━━━━━━━━━━<br><br>두 번째 문서를 드롭하세요")
                self.info_label.setAlignment(Qt.AlignCenter)
                self.info_label.setStyleSheet("padding: 20px; background: #E8F4F8; border: 3px solid #00A9FF; border-radius: 8px; color: #012433; font-size: 11pt;")
                
                # 첫 번째 문서 내용 미리보기 표시
                try:
                    preview_text = app_logic.extract_text_from_file(dropped, max_chars=1000)
                    self.text_preview.setText(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
                                              f"📄 첫 번째 문서: {filename}\n" +
                                              f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n" +
                                              preview_text)
                except Exception as e:
                    self.text_preview.setText(f"문서 미리보기 오류: {str(e)}")
            else:
                self.handle_1v1(self.first_file_path, dropped)
                self.first_file_path = None

    # [수정됨] app_ui.py 내부 SimilarDocScanPage 클래스

    def handle_1v1(self, f1, f2):
        print(f"\n{'='*60}")
        print(f"📄 문서 1:1 비교 시작")
        print(f"파일 1: {f1}")
        print(f"파일 2: {f2}")
        
        self.info_label.setText("📊 비교 분석 중...")
        self.info_label.setAlignment(Qt.AlignCenter)
        QApplication.processEvents()
        
        try:
            # 첫 번째 문서는 저장된 텍스트 사용 (이미 읽었음)
            if self.first_doc_text is not None:
                t1 = self.first_doc_text
                print(f"✅ 첫 번째 문서 텍스트 캐시 사용")
            else:
                t1 = app_logic.extract_text_from_file(f1, max_chars=20000000)
                print(f"⚠️ 첫 번째 문서 텍스트 새로 읽음")
            
            # 두 번째 문서는 새로 읽기
            t2 = app_logic.extract_text_from_file(f2, max_chars=20000000)
            
            print(f"텍스트 1 길이: {len(t1)} 자")
            print(f"텍스트 2 길이: {len(t2)} 자")
            
            if not t1 or not t2:
                self.info_label.setText("⚠️ 문서에서 텍스트를 추출할 수 없습니다.")
                print("❌ 텍스트 추출 실패")
                return
            
            score = app_logic.calculate_text_similarity(t1, t2)
            print(f"✅ 계산된 유사도: {score:.2f}%")
            
            filename1 = os.path.basename(f1)
            filename2 = os.path.basename(f2)
            
            # --- 드래그 앤 드롭 영역에 유사도 크게 표시 (이미지와 동일한 스타일) ---
            result_text = (f"<b style='font-size: 14pt;'>📄 문서 비교 결과</b><br><br>"
                           f"<div style='background: white; padding: 10px; border-radius: 6px; margin: 5px;'>"
                           f"<b style='color: #00A9FF;'>🔷 첫 번째</b><br>"
                           f"<span style='font-size: 9pt;'>{filename1}</span></div><br>"
                           f"<div style='background: white; padding: 10px; border-radius: 6px; margin: 5px;'>"
                           f"<b style='color: #89CFF3;'>🔷 두 번째</b><br>"
                           f"<span style='font-size: 9pt;'>{filename2}</span></div><br><br>"
                           f"<div style='background: white; padding: 20px; border-radius: 8px; border: 3px solid #0078D7;'>"
                           f"<b style='font-size: 12pt;'>📊 유사도</b><br>"
                           f"<span style='font-size: 32pt; color: #0078D7; font-weight: bold;'>{score:.1f}%</span></div>")
            
            self.info_label.setText(result_text)
            self.info_label.setAlignment(Qt.AlignCenter)
            self.info_label.setStyleSheet("padding: 20px; font-size: 10pt; background: #E8F4F8; border-radius: 8px; color: #012433;")
        
            # --- 오른쪽 미리보기 창 업데이트 (위/아래 분리) ---
            # 아래쪽: 두 번째 문서만 업데이트 (위쪽은 첫 번째 선택 시 이미 표시되어 있음)
            print(f"📝 두 번째 문서 미리보기 업데이트 시작...")
            print(f"   파일명: {filename2}")
            print(f"   텍스트 길이: {len(t2)} 자")
            print(f"   미리보기 길이: {len(t2[:1500])} 자")
            
            bottom_text = f"📄 두 번째 문서: {filename2}\n{'='*50}\n\n{t2[:1500]}"
            self.text_preview_bottom.setText(bottom_text)
            self.text_preview_bottom.setStyleSheet("background-color: #FFFFFF; color: #012433; border: 3px solid #89CFF3; border-radius: 6px; padding: 10px; font-size: 10pt;")
            
            print(f"✅ 두 번째 문서 미리보기 업데이트 완료")
            print(f"   위젯 visible: {self.text_preview_bottom.isVisible()}")
            print(f"   위젯 height: {self.text_preview_bottom.height()}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            error_msg = f"⚠️ 문서 비교 중 오류 발생:\n{str(e)}"
            self.info_label.setText(error_msg)
            self.info_label.setAlignment(Qt.AlignCenter)
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()
        
    def handle_folder_scan(self, folder):
        self.info_label.setText("폴더 내 문서 스캔 및 텍스트 추출 중...")
        QApplication.processEvents()
        groups = app_logic.find_similar_docs_from_folder(folder, self.threshold_slider.value())
        self.populate_table(groups)
        self.info_label.setText(f"스캔 완료. {len(groups)}개 그룹 발견.")

    def handle_multiple_scan(self, files):
        self.info_label.setText("파일 목록 분석 중...")
        QApplication.processEvents()
        groups = app_logic.find_similar_docs_from_list(files, self.threshold_slider.value())
        self.populate_table(groups)
        self.info_label.setText(f"분석 완료. {len(groups)}개 그룹 발견.")

    def populate_table(self, groups):
        self.result_table.setRowCount(0)
        for i, group in enumerate(groups):
            r = self.result_table.rowCount()
            self.result_table.insertRow(r)
            self.result_table.setSpan(r, 0, 1, 2)
            self.result_table.setItem(r, 0, QTableWidgetItem(f"📄 문서 그룹 {i+1}"))
            self.result_table.item(r, 0).setBackground(QColor("#3A5A3A"))
            
            for path, score in group:
                r = self.result_table.rowCount()
                self.result_table.insertRow(r)
                self.result_table.setItem(r, 0, QTableWidgetItem(path))
                self.result_table.setItem(r, 1, QTableWidgetItem(f"{score:.1f}%"))

    def on_doc_double_clicked(self, row, col):
        """더블클릭 시 문서 1:1 비교"""
        print("\n" + "="*70)
        print("🔔 문서 더블클릭 이벤트")
        print(f"클릭 위치: row={row}, col={col}")
        
        path_item = self.result_table.item(row, 0)
        if not path_item:
            print("❌ path_item이 None입니다")
            return
        
        clicked_path = path_item.text()
        print(f"📁 클릭한 경로: {clicked_path}")
        
        # 그룹 헤더인 경우 무시
        if not os.path.isfile(clicked_path):
            print(f"⚠️ 파일이 아닙니다 (그룹 헤더)")
            return
        
        print(f"✅ 유효한 파일입니다!")
        
        # 첫 번째 선택
        if not self.first_selected_doc:
            self.first_selected_doc = clicked_path
            filename = os.path.basename(clicked_path)
            print(f"📌 첫 번째 문서로 설정: {filename}")
            
            # 드래그 앤 드롭 영역 업데이트
            self.info_label.setText(f"<b style='font-size: 14pt;'>📄 문서 선택</b><br><br>"
                                   f"<div style='background: white; padding: 15px; border-radius: 8px; border: 3px solid #00A9FF;'>"
                                   f"<b style='color: #00A9FF; font-size: 12pt;'>🔷 첫 번째 문서 선택 완료</b><br><br>"
                                   f"<span style='font-size: 10pt;'>{filename}</span></div><br><br>"
                                   f"<span style='font-size: 11pt;'>두 번째 문서를 더블클릭하세요</span>")
            self.info_label.setAlignment(Qt.AlignCenter)
            self.info_label.setStyleSheet("padding: 20px; background: #E8F4F8; border-radius: 8px; color: #012433;")
            
            # 첫 번째 문서 내용 미리보기 표시 (위쪽)
            try:
                # 첫 번째 문서의 전체 텍스트를 저장 (비교용)
                self.first_doc_text = app_logic.extract_text_from_file(clicked_path, max_chars=20000000)
                preview_text = self.first_doc_text[:1500]
                self.text_preview_top.setText(f"📄 첫 번째 문서: {filename}\n"
                                              f"{'='*50}\n\n"
                                              f"{preview_text}")
                self.text_preview_bottom.clear()
                self.text_preview_bottom.setPlaceholderText("📄 두 번째 문서를 더블클릭하세요")
            except Exception as e:
                self.text_preview_top.setText(f"문서 미리보기 오류: {str(e)}")
                self.first_doc_text = None
        else:
            # 두 번째 선택 - 비교 실행
            filename2 = os.path.basename(clicked_path)
            print(f"📊 두 번째 문서 선택 -> 유사도 비교 시작")
            print(f"📌 두 번째 문서: {filename2}")
            print(f"🔄 비교 시작: {os.path.basename(self.first_selected_doc)} vs {filename2}")
            self.handle_1v1(self.first_selected_doc, clicked_path)
            self.first_selected_doc = None
            self.first_doc_text = None  # 캐시 초기화
            print(f"✅ 비교 완료 및 초기화")
            


# --- 통합 스캐너 화면 (UI 클래스) ---
class UnifiedScanPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setAcceptDrops(True)
        self.folder_path = None
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 왼쪽: 드롭 존 및 제어 패널
        left_layout = QVBoxLayout()
        self.info_label = QLabel("\n\n분석할 폴더를\n이곳으로 드래그 앤 드롭하세요.\n(아래에서 검사할 항목을 선택하세요)\n\n")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("DropZone")
        self.info_label.setMinimumHeight(150)
        
        # 슬라이더 및 체크박스 컨트롤 프레임
        slider_frame = QFrame()
        slider_frame.setFrameShape(QFrame.StyledPanel)
        slider_frame.setStyleSheet("background-color: #F5FBFF; border-radius: 4px; padding: 15px;")
        slider_layout = QVBoxLayout(slider_frame)
        
        # --- 1. 이미지 설정 (체크박스 + 슬라이더) ---
        img_layout = QHBoxLayout()
        self.chk_img = QCheckBox("이미지 검사")
        self.chk_img.setChecked(True) # 기본값 체크
        self.chk_img.setStyleSheet("font-weight: bold; color: #012433;")
        
        self.image_slider = QSlider(Qt.Horizontal)
        self.image_slider.setRange(1, 20)
        self.image_slider.setValue(10)
        self.image_slider.setEnabled(True)
        
        img_label = QLabel(f"기준: 10")
        img_label.setMinimumWidth(60)
        img_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # 슬라이더 값 변경 시 라벨 업데이트
        self.image_slider.valueChanged.connect(lambda v: img_label.setText(f"기준: {v}"))
        # 체크박스 변경 시 슬라이더 활성/비활성
        self.chk_img.toggled.connect(self.image_slider.setEnabled)

        img_layout.addWidget(self.chk_img)
        img_layout.addWidget(self.image_slider)
        img_layout.addWidget(img_label)
        slider_layout.addLayout(img_layout)
        
        # --- 2. 비디오 설정 ---
        vid_layout = QHBoxLayout()
        self.chk_vid = QCheckBox("비디오 검사")
        self.chk_vid.setChecked(True)
        self.chk_vid.setStyleSheet("font-weight: bold; color: #012433;")
        
        self.video_slider = QSlider(Qt.Horizontal)
        self.video_slider.setRange(30, 95)
        self.video_slider.setValue(60)
        
        vid_label = QLabel(f"기준: 60%")
        vid_label.setMinimumWidth(60)
        vid_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.video_slider.valueChanged.connect(lambda v: vid_label.setText(f"기준: {v}%"))
        self.chk_vid.toggled.connect(self.video_slider.setEnabled)
        
        vid_layout.addWidget(self.chk_vid)
        vid_layout.addWidget(self.video_slider)
        vid_layout.addWidget(vid_label)
        slider_layout.addLayout(vid_layout)
        
        # --- 3. 문서 설정 ---
        doc_layout = QHBoxLayout()
        self.chk_doc = QCheckBox("문서 검사")
        self.chk_doc.setChecked(True)
        self.chk_doc.setStyleSheet("font-weight: bold; color: #012433;")
        
        self.doc_slider = QSlider(Qt.Horizontal)
        self.doc_slider.setRange(30, 95)
        self.doc_slider.setValue(75)
        
        doc_label = QLabel(f"기준: 75%")
        doc_label.setMinimumWidth(60)
        doc_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.doc_slider.valueChanged.connect(lambda v: doc_label.setText(f"기준: {v}%"))
        self.chk_doc.toggled.connect(self.doc_slider.setEnabled)

        doc_layout.addWidget(self.chk_doc)
        doc_layout.addWidget(self.doc_slider)
        doc_layout.addWidget(doc_label)
        slider_layout.addLayout(doc_layout)
        
        # --- 검사 시작 버튼 추가 ---
        self.scan_btn = QPushButton("🔍 검사 시작")
        self.scan_btn.setObjectName("FunctionButton")
        self.scan_btn.setMinimumHeight(45)
        self.scan_btn.clicked.connect(self.start_scan)
        
        left_layout.addWidget(self.info_label, 1)
        left_layout.addWidget(slider_frame, 0)
        left_layout.addWidget(self.scan_btn)

        # 오른쪽: 결과 표시 (탭 형태)
        right_layout = QVBoxLayout()
        
        # 결과 레이블
        result_title = QLabel("분석 결과")
        result_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #012433;")
        
        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setObjectName("ResultTable")
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels(["유형", "그룹 수", "세부"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        
        # 상세 정보 패널
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("결과를 클릭하면 상세 정보가 여기에 표시됩니다.")
        self.details_text.setStyleSheet("background-color: #FFFFFF; color: #012433; border: 1px solid #A0E9FF;")
        
        # 버튼
        reset_btn = QPushButton("다시 하기")
        reset_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        reset_btn.clicked.connect(self.reset_page)
        back_btn = QPushButton("뒤로 가기")
        back_btn.clicked.connect(lambda: self.controller.setCurrentIndex(0))
        
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(back_btn)
        
        right_layout.addWidget(result_title)
        right_layout.addWidget(self.result_table, 1)
        right_layout.addWidget(QLabel("상세 정보:"))
        right_layout.addWidget(self.details_text, 1)
        right_layout.addLayout(button_layout)
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        
        self.unified_results = {}

    def reset_page(self):
        self.folder_path = None
        self.info_label.setText("\n\n분석할 폴더를\n이곳으로 드래그 앤 드롭하세요.\n(아래에서 검사할 항목을 선택하세요)\n\n")
        self.info_label.setStyleSheet("")
        self.result_table.setRowCount(0)
        self.details_text.clear()
        self.unified_results = {}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.info_label.setText("\n\n좋습니다! 여기에 놓으세요.\n\n")
            self.info_label.setStyleSheet("border-color: #00A9FF; color: #012433;")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if not self.folder_path:
            self.reset_page()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if not files:
            return
        
        folder_path = files[0]
        if not os.path.isdir(folder_path):
            self.info_label.setText("⚠️ 폴더를 드롭해주세요.")
            return
        
        self.folder_path = folder_path
        self.info_label.setText(f"✅ 폴더 로드 완료: {os.path.basename(folder_path)}\n체크박스를 선택하고 '검사 시작' 버튼을 누르세요.")

    def start_scan(self):
        """검사 시작 버튼 클릭 시 호출"""
        if not self.folder_path:
            QMessageBox.warning(self, "경고", "먼저 폴더를 드래그 앤 드롭해주세요.")
            return
        
        # 1. 체크박스 상태 확인
        do_img = self.chk_img.isChecked()
        do_vid = self.chk_vid.isChecked()
        do_doc = self.chk_doc.isChecked()
        
        if not (do_img or do_vid or do_doc):
            QMessageBox.warning(self, "경고", "최소 하나 이상의 검사 항목을 선택해주세요.")
            return

        status_msg = f"🔄 분석 중... ({os.path.basename(self.folder_path)})"
        self.info_label.setText(status_msg)
        self.scan_btn.setEnabled(False)
        QApplication.processEvents()
        
        image_threshold = self.image_slider.value()
        video_threshold = self.video_slider.value()
        doc_threshold = self.doc_slider.value()
        
        try:
            # 2. 로직 함수 호출 시 체크박스 상태(scan_xxx) 전달
            self.unified_results = app_logic.unified_scan_folder(
                self.folder_path,
                image_threshold=image_threshold,
                video_threshold=video_threshold,
                doc_threshold=doc_threshold,
                scan_img=do_img,
                scan_vid=do_vid,
                scan_doc=do_doc
            )
            
            self.populate_results()
            
            total_groups = (len(self.unified_results.get('images', [])) +
                           len(self.unified_results.get('videos', [])) +
                           len(self.unified_results.get('documents', [])))
            self.info_label.setText(f"✅ 분석 완료.\n총 {total_groups}개 그룹 발견")
        except Exception as e:
            self.info_label.setText(f"❌ 분석 오류: {str(e)}")
            print(f"통합 스캔 오류: {e}")
        finally:
            self.scan_btn.setEnabled(True)

    def populate_results(self):
        self.result_table.setRowCount(0)
        
        # 이미지 결과 (체크했을 때만 표시하거나, 결과가 비어있으면 0으로 표시)
        if self.chk_img.isChecked():
            img_groups = self.unified_results.get('images', [])
            self._add_result_row("🖼️ 이미지", len(img_groups), "#CDF5FD")

        # 비디오 결과
        if self.chk_vid.isChecked():
            vid_groups = self.unified_results.get('videos', [])
            self._add_result_row("🎬 비디오", len(vid_groups), "#A0E9FF")
        
        # 문서 결과
        if self.chk_doc.isChecked():
            doc_groups = self.unified_results.get('documents', [])
            self._add_result_row("📄 문서", len(doc_groups), "#89CFF3")
        
        # 기본 상세 정보 텍스트
        summary = "📊 스캔 결과 요약\n\n"
        if self.chk_img.isChecked():
            summary += f"이미지 그룹: {len(self.unified_results.get('images', []))}개\n"
        if self.chk_vid.isChecked():
            summary += f"비디오 그룹: {len(self.unified_results.get('videos', []))}개\n"
        if self.chk_doc.isChecked():
            summary += f"문서 그룹: {len(self.unified_results.get('documents', []))}개\n"
            
        self.details_text.setText(summary)

    def _add_result_row(self, type_name, count, bg_color):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        type_item = QTableWidgetItem(type_name)
        type_item.setBackground(QColor(bg_color))
        
        count_item = QTableWidgetItem(str(count))
        
        detail_msg = f"{count}개 그룹 발견" if count > 0 else "유사 항목 없음"
        detail_item = QTableWidgetItem(detail_msg)
        
        self.result_table.setItem(row, 0, type_item)
        self.result_table.setItem(row, 1, count_item)
        self.result_table.setItem(row, 2, detail_item)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("하루 정리")
        self.setGeometry(200, 200, 1000, 650) 
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 메인 윈도우에서 공유할 변수들
        self.dropped_files = []
        self.folder_path = None
        
        # 페이지 생성
        self.main_drop_page = MainDropAnalyzePage(self.stacked_widget)
        self.duplicate_page = DuplicateCheckPage(self.stacked_widget)
        self.similar_image_page = SimilarImageScanPage(self.stacked_widget)
        self.iqa_page = ImageQualityPage(self.stacked_widget)
        self.similar_video_page = SimilarVideoScanPage(self.stacked_widget)
        self.similar_doc_page = SimilarDocScanPage(self.stacked_widget)
        self.unified_scan_page = UnifiedScanPage(self.stacked_widget)
        
        # 페이지 추가 (index 순서 중요)
        self.stacked_widget.addWidget(self.main_drop_page)      # index 0
        self.stacked_widget.addWidget(self.duplicate_page)      # index 1
        self.stacked_widget.addWidget(self.similar_image_page)  # index 2
        self.stacked_widget.addWidget(self.iqa_page)            # index 3
        self.stacked_widget.addWidget(self.similar_video_page)  # index 4
        self.stacked_widget.addWidget(self.similar_doc_page)    # index 5
        self.stacked_widget.addWidget(self.unified_scan_page)   # index 6

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    if getattr(sys, 'frozen', False):
        # exe로 실행될 때: 실제 exe 파일이 있는 폴더를 기준(base_dir)으로 잡음
        base_dir = os.path.dirname(sys.executable)
    else:
        # 파이썬으로 실행될 때: 현재 파일 위치를 기준으로 잡음
        base_dir = os.path.dirname(os.path.abspath(__file__))

    style_file_path = os.path.join(base_dir, "style.qss")
    
    print(f"스타일시트 로드 시도: {style_file_path}")
    
    style_str = load_stylesheet(style_file_path)
    
    if style_str:
        app.setStyleSheet(style_str)
        print("스타일시트 적용 성공.")
    else:
        print("스타일시트 적용 실패. (파일을 찾지 못했거나 내용이 비어있습니다)")
    
    # 밝은 팔레트 적용 (사용자 요청: 어두운 색 대신 밝은 테마, 지정 색상 사용)
    light_palette = QPalette()
    # 배경과 텍스트: 밝은 배경, 짙은 텍스트
    light_palette.setColor(QPalette.Window, QColor('#EAF8FF'))        # 페이지 배경 (밝은 하늘색)
    light_palette.setColor(QPalette.WindowText, QColor('#012433'))
    light_palette.setColor(QPalette.Base, QColor('#FFFFFF'))          # 입력/테이블 배경
    light_palette.setColor(QPalette.AlternateBase, QColor('#CDF5FD')) # 대체 배경
    light_palette.setColor(QPalette.ToolTipBase, QColor('#012433'))
    light_palette.setColor(QPalette.ToolTipText, QColor('#FFFFFF'))
    light_palette.setColor(QPalette.Text, QColor('#012433'))
    # 버튼과 하이라이트: 지정된 팔레트 색상 사용
    light_palette.setColor(QPalette.Button, QColor('#00A9FF'))        # 주요 버튼 색
    light_palette.setColor(QPalette.ButtonText, QColor('#FFFFFF'))
    light_palette.setColor(QPalette.BrightText, QColor('#FF6B6B'))
    light_palette.setColor(QPalette.Link, QColor('#00A9FF'))
    light_palette.setColor(QPalette.Highlight, QColor('#89CFF3'))     # 선택/하이라이트
    light_palette.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))
    app.setPalette(light_palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())