# 파일 이름: app_logic.py
from iqa_scorer import hybrid_scorer, IQA_AVAILABLE

import os
import hashlib
from collections import defaultdict
import mimetypes
import math
import io  # <-- [수정] 바이트 처리를 위해 io 모듈 추가

# --- 필요한 라이브러리 임포트 ---
import cv2
from skimage.metrics import structural_similarity as ssim
import numpy as np
import imagehash
from PIL import Image
from difflib import SequenceMatcher
import difflib
import zlib
import struct


# --- 헬퍼 함수 (변경 없음) ---

def format_bytes(size):
    """파일 크기를 읽기 쉬운 GB/MB/KB 등으로 변환"""
    if size == 0: return "0 B"
    power_labels = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    i = min(int(math.log(size, 1024)), len(power_labels) - 1)
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {power_labels[i]}"

# --- 확장자 기반 이미지 인식 로직 추가 ---
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.ico')
# ----------------------------------------

# app_logic.py 파일 내 get_file_category 함수 교체

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.ico')

def get_file_category(filepath):
    """
    파일 경로를 기반으로 카테고리(이미지, 영상 등) 반환.
    확장자 기반으로 이미지 파일을 우선적으로 인식합니다.
    """
    filename = filepath.lower()
    
    # 1. 확장자 기반 체크 (JPEG, PNG 등)
    if filename.endswith(IMAGE_EXTENSIONS): 
        return "Images"
    
    # 2. MIME Type 기반 체크 (나머지 파일들)
    import mimetypes # 함수 내에서 임포트 (안전성 확보)
    mime_type, _ = mimetypes.guess_type(filepath)
    
    if mime_type:
        main_type = mime_type.split('/')[0]
        if main_type == "video": return "Videos"
        if main_type == "audio": return "Audio"
        if main_type == "text": return "Documents"
    
    # MIME 타입이 없거나 다른 모든 경우
    return "Other"

# --- 중복 파일 검사 (DuplicateCheckPage) 로직 ---

def get_file_hashes(filepath):
    """파일의 MD5와 SHA256 해시를 반환"""
    # [참고] 'rb' (read binary) 모드는 한글 경로와 상관없이 잘 동작합니다. (변경 불필요)
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            md5_hash.update(chunk)
            sha256_hash.update(chunk)
    return md5_hash.hexdigest(), sha256_hash.hexdigest()

def find_duplicate_files(folder_path):
    """폴더를 스캔하여 중복 파일 목록과 통계 정보를 반환"""
    # [참고] os.walk, os.path.getsize 등은 현대 파이썬에서 한글 경로를 잘 지원합니다. (변경 불필요)
    hash_map = defaultdict(list)
    total_files_scanned = 0
    total_size_scanned = 0
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            total_files_scanned += 1
            full_path = os.path.join(root, filename)
            try:
                file_size = os.path.getsize(full_path)
                total_size_scanned += file_size
                md5_val, sha_val = get_file_hashes(full_path)
                combined_key = f"{md5_val}_{sha_val}"
                hash_map[combined_key].append(full_path)
            except Exception as e:
                print(f"❌ 오류 발생: {full_path} → {e}")
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return duplicates, total_files_scanned, total_size_scanned


# --- 유사 이미지 스캔 (SimilarImageScanPage) 로직 ---

def get_image_similarity(file1_path, file2_path):
    """[수정] 두 이미지 파일의 SSIM, pHash 유사도를 '바이트' 기반으로 반환"""
    try:
        # --- [수정] ---
        # 1. 파일을 파이썬의 open()으로 직접 읽습니다. (한글 경로 문제 해결)
        with open(file1_path, 'rb') as f:
            img_bytes1 = f.read()
        with open(file2_path, 'rb') as f:
            img_bytes2 = f.read()
            
        # 2. Pillow(Image)를 경로가 아닌 바이트(BytesIO)로 엽니다.
        image1_pil = Image.open(io.BytesIO(img_bytes1))
        image2_pil = Image.open(io.BytesIO(img_bytes2))
        # --- [수정 끝] ---

        hash1 = imagehash.phash(image1_pil)
        hash2 = imagehash.phash(image2_pil)
        hash_diff = hash1 - hash2 
        phash_similarity = (64 - hash_diff) / 64 * 100

        # --- [수정] ---
        # 3. np.fromfile(경로) 대신 np.frombuffer(바이트)를 사용합니다. (한글 경로 문제 해결)
        np_array1 = np.frombuffer(img_bytes1, np.uint8)
        np_array2 = np.frombuffer(img_bytes2, np.uint8)
        # --- [수정 끝] ---

        image1_cv = cv2.imdecode(np_array1, cv2.IMREAD_GRAYSCALE)
        image2_cv = cv2.imdecode(np_array2, cv2.IMREAD_GRAYSCALE)
        
        if image1_cv is None or image2_cv is None:
            raise ValueError("OpenCV 이미지 로드 실패")

        if image1_cv.shape != image2_cv.shape:
            h, w = image2_cv.shape
            image1_cv = cv2.resize(image1_cv, (w, h))

        ssim_score = ssim(image1_cv, image2_cv) * 100
        
        return (ssim_score, phash_similarity, hash_diff)
    except Exception as e:
        print(f"Similarity error: {e}")
        return (None, None, None)

def group_hashes(hashes_dict, threshold):
    """해시 딕셔너리를 받아 유사도 임계값 기준으로 그룹화 (변경 없음)"""
    image_paths = list(hashes_dict.keys())
    groups = []
    processed = set()
    for i in range(len(image_paths)):
        path1 = image_paths[i]
        if path1 in processed: continue
        current_group = {path1: 100.0}
        hash1 = hashes_dict[path1]
        for j in range(i + 1, len(image_paths)):
            path2 = image_paths[j]
            if path2 in processed: continue
            hash2 = hashes_dict[path2]
            diff = hash1 - hash2
            if diff <= threshold:
                similarity = (64 - diff) / 64 * 100
                current_group[path2] = similarity
                processed.add(path2)
        if len(current_group) > 1:
            processed.add(path1)
            sorted_group = sorted(current_group.items(), key=lambda item: item[1], reverse=True)
            groups.append(sorted_group)
    return groups

def find_similar_images_from_folder(folder_path, threshold):
    """[수정] 폴더 내의 이미지들을 '바이트' 기반으로 스캔하여 유사 그룹 반환"""
    hashes = {}
    image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if not filename.lower().endswith(image_extensions): continue
            full_path = os.path.join(root, filename)
            try:
                # --- [수정] ---
                # Image.open(경로) 대신, 바이트로 읽어서 Image.open(BytesIO) 사용
                with open(full_path, 'rb') as f:
                    img_bytes = f.read()
                with Image.open(io.BytesIO(img_bytes)) as img:
                    hashes[full_path] = imagehash.phash(img)
                # --- [수정 끝] ---
            except Exception as e: 
                print(f"❌ 이미지 해시 생성 오류: {full_path} → {e}")
    return group_hashes(hashes, threshold)

def find_similar_images_from_list(file_list, threshold):
    """[수정] 파일 리스트 내의 이미지들을 '바이트' 기반으로 스캔하여 유사 그룹 반환"""
    hashes = {}
    for full_path in file_list:
        if not os.path.isfile(full_path): continue
        try:
            # --- [수정] ---
            # Image.open(경로) 대신, 바이트로 읽어서 Image.open(BytesIO) 사용
            with open(full_path, 'rb') as f:
                img_bytes = f.read()
            with Image.open(io.BytesIO(img_bytes)) as img:
                hashes[full_path] = imagehash.phash(img)
            # --- [수정 끝] ---
        except Exception as e: 
            print(f"❌ 이미지 해시 생성 오류: {full_path} → {e}")
    return group_hashes(hashes, threshold)

# app_logic.py 파일에 추가

# app_logic.py 파일 끝 부분에 추가

def analyze_image_quality_in_folder(folder_path):
    """
    폴더를 스캔하여 이미지 품질 점수를 계산하고 결과를 반환합니다.
    (iqa_scorer.py의 로직을 호출)
    """
    # [주의] 이 함수가 실행되려면 파일 상단에 'from iqa_scorer import hybrid_scorer, IQA_AVAILABLE'이 있어야 합니다.
    from iqa_scorer import hybrid_scorer, IQA_AVAILABLE

    processed_groups = []
    total_best_shots_found = 0

    if not IQA_AVAILABLE or hybrid_scorer is None:
        # IQA 기능이 비활성화된 경우
        return [], False 

    image_paths = []
    # 폴더 내 모든 파일을 순회하며 이미지 파일 경로를 수집
    for root, _, files in os.walk(folder_path):
        for filename in files:
            full_path = os.path.join(root, filename)
            # 수정된 get_file_category 함수를 사용해 이미지인지 확인
            if get_file_category(full_path) == "Images":
                image_paths.append(full_path)
    
    if not image_paths:
        return [], True # 이미지가 없으므로 정상 종료

    results = [] 
    
    # 1. 수집된 이미지 경로를 IQA 스코어러로 분석
    for path in image_paths:
        # [안전 모드] 충돌 대비: 데이터 구조를 미리 정의 (KeyError 방지)
        iqa_score_data = {
            "final_score": 0.0, 
            "technical": 0.0, 
            "aesthetic": 0.0, 
            "raw_metrics": {"raw_laplacian": 0.0, "raw_brisque": 0.0, "raw_brightness": 127.0},
            "penalty_applied": True, 
        }
        
        try:
            # IQA_Scorer의 analyze_image 함수 호출
            score_data = hybrid_scorer.analyze_image(path) 
            results.append({
                'path': path,
                'category': get_file_category(path),
                'size': os.path.getsize(path),
                'score_data': score_data # 완성된 점수 구조
            })
        except Exception as e:
            # 오류 발생 시, 0점짜리 안전모드 데이터를 사용하거나 건너뜁니다.
            # 여기서는 오류가 난 파일은 제외하고 건너뜁니다.
            print(f"❌ 품질 분석 오류 ({os.path.basename(path)}): {e}")
            continue # 오류 난 파일은 결과에 포함하지 않고 다음 파일로 이동
            
    # 2. 최종 점수(final_score) 기준으로 내림차순 정렬
    results.sort(key=lambda x: x['score_data']['final_score'], reverse=True)
    
    return results, True


# --- 유사 비디오 스캔 로직 ---

def extract_video_fingerprint(video_path, num_frames=10):
    """
    비디오에서 균등한 간격으로 num_frames만큼 프레임을 추출하여
    각 프레임의 pHash 리스트를 반환합니다.
    """
    hashes = []
    
    # [주의] Windows에서 opencv의 VideoCapture는 한글 경로에 취약할 수 있습니다.
    # 만약 열리지 않는다면 경로를 그대로 넣지 말고 임시 파일 등을 활용해야 할 수 있으나,
    # 최신 opencv-python은 대부분 지원합니다.
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return None # 비디오 열기 실패
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return None

    # 프레임 추출 간격 계산
    step = total_frames // (num_frames + 1)
    
    current_frame = step
    for _ in range(num_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()
        if ret:
            # OpenCV(BGR) -> PIL Image 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            
            # pHash 계산
            phash = imagehash.phash(pil_img)
            hashes.append(phash)
        
        current_frame += step
        
    cap.release()
    
    # 추출된 프레임이 너무 적으면 실패 처리
    if len(hashes) < num_frames // 2:
        return None
        
    return hashes

def calculate_video_similarity(hashes1, hashes2):
    """
    두 비디오의 해시 리스트를 비교하여 유사도(0~100%) 반환
    """
    if not hashes1 or not hashes2:
        return 0.0
    
    # 더 짧은 길이에 맞춤
    min_len = min(len(hashes1), len(hashes2))
    match_count = 0
    
    # 해밍 거리 임계값 (이미지 유사도와 동일하게 설정, 예: 10 이하)
    HAMMING_THRESHOLD = 10 
    
    for i in range(min_len):
        diff = hashes1[i] - hashes2[i]
        if diff <= HAMMING_THRESHOLD:
            match_count += 1
            
    return (match_count / min_len) * 100.0

def group_video_hashes(hashes_dict, threshold):
    """비디오 해시 딕셔너리를 받아 유사도 임계값(%) 기준으로 그룹화"""
    video_paths = list(hashes_dict.keys())
    groups = []
    processed = set()
    
    for i in range(len(video_paths)):
        path1 = video_paths[i]
        if path1 in processed: continue
        
        current_group = {path1: 100.0}
        hashes1 = hashes_dict[path1]
        
        for j in range(i + 1, len(video_paths)):
            path2 = video_paths[j]
            if path2 in processed: continue
            
            hashes2 = hashes_dict[path2]
            
            # 두 비디오의 유사도 계산 (0~100.0)
            similarity = calculate_video_similarity(hashes1, hashes2)
            
            if similarity >= threshold:
                current_group[path2] = similarity
                processed.add(path2)
        
        if len(current_group) > 1:
            processed.add(path1)
            # 유사도 높은 순 정렬
            sorted_group = sorted(current_group.items(), key=lambda item: item[1], reverse=True)
            groups.append(sorted_group)
            
    return groups

def find_similar_videos_from_folder(folder_path, threshold):
    """폴더 내 비디오들을 스캔하여 유사 그룹 반환"""
    hashes = {}
    # 비디오 확장자 목록 (소문자)
    video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v')
    
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if not filename.lower().endswith(video_extensions): continue
            
            full_path = os.path.join(root, filename)
            try:
                # 프레임 추출 및 해싱 (기본 10프레임)
                vid_hashes = extract_video_fingerprint(full_path)
                if vid_hashes:
                    hashes[full_path] = vid_hashes
            except Exception as e: 
                print(f"❌ 비디오 해시 생성 오류: {full_path} → {e}")
                
    return group_video_hashes(hashes, threshold)

def find_similar_videos_from_list(file_list, threshold):
    """파일 리스트 내 비디오들을 스캔하여 유사 그룹 반환"""
    hashes = {}
    for full_path in file_list:
        if not os.path.isfile(full_path): continue
        try:
            vid_hashes = extract_video_fingerprint(full_path)
            if vid_hashes:
                hashes[full_path] = vid_hashes
        except Exception as e: 
            print(f"❌ 비디오 해시 생성 오류: {full_path} → {e}")
            
    return group_video_hashes(hashes, threshold)


# --- 문서 유사도 검사 로직 ---

# 라이브러리 로드 시도 (없을 경우 에러 방지)
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PyPDF2가 설치되지 않아 PDF 검사가 제한됩니다.")

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx가 설치되지 않아 DOCX 검사가 제한됩니다.")

try:
    import olefile
    HWP_AVAILABLE = True
except ImportError:
    HWP_AVAILABLE = False
    print("⚠️ olefile이 설치되지 않아 HWP 검사가 제한됩니다.")

def get_hwp_text(filename):
    """HWP 파일(5.0 버전 이상, OLE 포맷)에서 텍스트만 추출"""
    if not HWP_AVAILABLE: return ""
    
    # 파일이 실제 OLE 포맷인지 먼저 확인 (HWPX나 손상된 파일 방지)
    if not olefile.isOleFile(filename):
        return "" 

    text = ""
    try:
        f = olefile.OleFileIO(filename)
        dirs = f.listdir()
        
        # [수정] IndexError 방지를 위해 길이를 체크하며 섹션 찾기
        sections = []
        for d in dirs:
            # "BodyText" 폴더 안에 있는 파일만 대상 (길이가 2 이상이어야 함)
            if d[0] == "BodyText" and len(d) > 1:
                sections.append(d[1])
        
        sections.sort() # 섹션 순서대로 정렬 (Section0, Section1...)
        
        for section in sections:
            # 스트림 경로 조합 (예: "BodyText/Section0")
            bodytext = f.openstream(["BodyText", section]).read()
            
            # HWP 5.0 압축 해제 (zlib)
            try:
                # -15: 헤더 없는 Raw Deflate 시도 (대부분의 HWP)
                unpacked_data = zlib.decompress(bodytext, -15)
            except zlib.error:
                try:
                    # 실패 시 표준 zlib 시도
                    unpacked_data = zlib.decompress(bodytext)
                except:
                    # 압축이 안 된 경우 (매우 드묾)
                    unpacked_data = bodytext
            
            # UTF-16LE 디코딩
            decoded_text = unpacked_data.decode('utf-16le', errors='ignore')
            
            # 텍스트 정제
            text += decoded_text.replace('\r', '\n').replace('\x00', '') + "\n"
            
        f.close()
    except Exception as e:
        # 디버깅을 위해 에러 메시지 출력
        print(f"❌ HWP 내부 구조 분석 실패 ({filename}): {e}")
        return ""
        
    return text

def extract_text_from_file(filepath, max_chars=3000):
    """
    파일 확장자에 따라 적절한 방식으로 텍스트를 추출합니다.
    [수정 사항] SMI, SRT 등 자막 파일을 위해 UTF-16 및 Latin-1 폴백 추가
    """
    ext = os.path.splitext(filepath)[1].lower()
    text = ""

    # 1. PDF 파일 (PyPDF2 필요)
    if ext == '.pdf' and PDF_AVAILABLE:
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for i in range(min(5, len(reader.pages))):
                    page_text = reader.pages[i].extract_text()
                    if page_text: text += page_text
            return text[:max_chars].strip()
        except Exception as e:
            print(f"PDF 읽기 실패: {e}")
            return ""

    # 2. Word 파일 (python-docx 필요)
    elif ext == '.docx' and DOCX_AVAILABLE:
        try:
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
                if len(text) > max_chars: break
            return text[:max_chars].strip()
        except Exception as e:
            print(f"DOCX 읽기 실패: {e}")
            return ""
    
    # 3. HWP 파일 (olefile 필요)
    elif ext == '.hwp':
        try:
            extracted = get_hwp_text(filepath)
            if not extracted: pass 
            return extracted[:max_chars].strip()
        except Exception as e:
            print(f"HWP 읽기 실패: {e}")
            return ""
        
    # 4. 그 외 모든 파일 (자막 .smi, .srt 및 일반 텍스트)
    else:
        # 인코딩 시도 순서:
        # 1. utf-8-sig : BOM이 있는 UTF-8 (윈도우 메모장 저장 시 흔함) 및 일반 UTF-8
        # 2. cp949 : 한국어 윈도우 기본 인코딩 (대부분의 옛날 자막 파일)
        # 3. utf-16 : 최신 윈도우 메모장 기본 저장 방식
        # 4. latin-1 : 위 3개가 다 안 될 때, 깨지더라도 바이트를 문자로 강제 변환하여 읽음 (0% 방지)
        
        encodings = ['utf-8-sig', 'cp949', 'utf-16', 'latin-1']
        
        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    text = f.read(max_chars)
                # 읽기에 성공하면 반복문 탈출
                if text: break
            except (UnicodeDecodeError, UnicodeError):
                continue # 다음 인코딩 시도
            except Exception:
                break # 권한 문제 등 치명적 오류 시 중단

    return text.strip()

def calculate_text_similarity(text1, text2):
    """두 텍스트의 유사도를 0~100%로 반환 (SequenceMatcher 사용)"""
    if not text1 or not text2:
        return 0.0
    
    # difflib은 표준 라이브러리로, 텍스트 비교에 매우 강력합니다.
    matcher = difflib.SequenceMatcher(None, text1, text2)
    return matcher.ratio() * 100.0

def find_similar_docs_from_folder(folder_path, threshold):
    """폴더 내 문서들을 스캔하여 유사 그룹 반환"""
    
    # [복구 완료] 변수명을 원래대로 doc_extensions로 되돌렸습니다.
    # 단, 분석을 원하시는 .smi, .hwp, .srt는 목록에 포함되어야 인식이 가능합니다.
    doc_extensions = ('.txt', '.md', '.py', '.pdf', '.docx', '.hwp', '.smi', '.srt')
    
    docs = {}
    
    # 1. 텍스트 추출 단계
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            # 설정한 확장자로 끝나는 파일만 골라냅니다.
            if filename.lower().endswith(doc_extensions):
                full_path = os.path.join(root, filename)
                extracted_text = extract_text_from_file(full_path)
                
                # 내용이 너무 짧으면(10자 미만) 비교 제외
                if len(extracted_text) > 10:
                    docs[full_path] = extracted_text

    # 2. 비교 및 그룹화 단계 (기존 로직 그대로 유지)
    doc_paths = list(docs.keys())
    groups = []
    processed = set()
    
    for i in range(len(doc_paths)):
        path1 = doc_paths[i]
        if path1 in processed: continue
        
        current_group = {path1: 100.0}
        text1 = docs[path1]
        
        for j in range(i + 1, len(doc_paths)):
            path2 = doc_paths[j]
            if path2 in processed: continue
            
            text2 = docs[path2]
            similarity = calculate_text_similarity(text1, text2)
            
            if similarity >= threshold:
                current_group[path2] = similarity
                processed.add(path2)
        
        if len(current_group) > 1:
            processed.add(path1)
            sorted_group = sorted(current_group.items(), key=lambda item: item[1], reverse=True)
            groups.append(sorted_group)
            
    return groups


def find_similar_docs_from_list(file_list, threshold):
    """파일 리스트 내 문서들을 스캔하여 유사 그룹 반환"""
    docs = {}
    
    for full_path in file_list:
        if not os.path.isfile(full_path):
            continue
        extracted_text = extract_text_from_file(full_path)
        
        if len(extracted_text) > 10:
            docs[full_path] = extracted_text
    
    # 비교 및 그룹화 단계
    doc_paths = list(docs.keys())
    groups = []
    processed = set()
    
    for i in range(len(doc_paths)):
        path1 = doc_paths[i]
        if path1 in processed:
            continue
        
        current_group = {path1: 100.0}
        text1 = docs[path1]
        
        for j in range(i + 1, len(doc_paths)):
            path2 = doc_paths[j]
            if path2 in processed:
                continue
            
            text2 = docs[path2]
            similarity = calculate_text_similarity(text1, text2)
            
            if similarity >= threshold:
                current_group[path2] = similarity
                processed.add(path2)
        
        if len(current_group) > 1:
            processed.add(path1)
            sorted_group = sorted(current_group.items(), key=lambda item: item[1], reverse=True)
            groups.append(sorted_group)
    
    return groups


# --- 통합 스캔 함수 (UnifiedScanPage) 로직 ---

def unified_scan_folder(folder_path, image_threshold=10, video_threshold=60, doc_threshold=75, scan_img=True, scan_vid=True, scan_doc=True):
    """
    폴더를 스캔하여 선택된 유형(이미지, 비디오, 문서)의 유사도를 분석합니다.
    
    Parameters:
    - folder_path: 스캔할 폴더 경로
    - image_threshold: 이미지 임계값
    - video_threshold: 비디오 임계값
    - doc_threshold: 문서 임계값
    - scan_img: 이미지 스캔 여부 (Boolean)
    - scan_vid: 비디오 스캔 여부 (Boolean)
    - scan_doc: 문서 스캔 여부 (Boolean)
    """
    results = {
        'images': [],
        'videos': [],
        'documents': []
    }
    
    # 1. 이미지 스캔 (선택 시에만 실행)
    if scan_img:
        try:
            results['images'] = find_similar_images_from_folder(folder_path, image_threshold)
        except Exception as e:
            print(f"❌ 이미지 스캔 오류: {e}")
    
    # 2. 비디오 스캔 (선택 시에만 실행)
    if scan_vid:
        try:
            results['videos'] = find_similar_videos_from_folder(folder_path, video_threshold)
        except Exception as e:
            print(f"❌ 비디오 스캔 오류: {e}")
    
    # 3. 문서 스캔 (선택 시에만 실행)
    if scan_doc:
        try:
            results['documents'] = find_similar_docs_from_folder(folder_path, doc_threshold)
        except Exception as e:
            print(f"❌ 문서 스캔 오류: {e}")
    
    return results