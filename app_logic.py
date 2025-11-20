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