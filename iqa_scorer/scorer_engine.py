# 파일 이름: iqa_scorer/scorer_engine.py (전체 내용)

import cv2
import numpy as np
import torch
import io
import math
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

# 이 클래스가 모든 계산을 수행합니다.
class HybridScorer:
    def __init__(self, device='cpu'):
        # 1. 가중치 및 상수 정의 (BRISQUE 제거 후 비율 재조정)
        self.W_AESTHETIC = 0.65  # 미적 점수 가중치 (CLIP)
        self.W_TECHNICAL = 0.35  # 기술 점수 가중치 (Laplacian만 사용)
        self.LAPLACIAN_MAX = 1500.0 # Laplacian 정규화 기준
        self.BRIGHT_LOWER = 30.0
        self.BRIGHT_UPPER = 220.0
        
        # 2. CLIP 모델 로드
        self.device = device
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    # --- A. 기술적 지표 추출 ---
    def get_technical_metrics(self, image_path):
        # 1. 파일 읽기 (안전한 바이트 처리)
        with open(image_path, 'rb') as f:
            img_bytes = f.read()

        # 2. OpenCV 로드 및 계산
        np_array = np.frombuffer(img_bytes, np.uint8)
        img_cv = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if img_cv is None: raise FileNotFoundError("OpenCV 디코딩 실패.")

        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var() 
        brightness = np.mean(gray)
        
        # BRISQUE 자리에 0.0을 반환 (사용하지 않음)
        return blur_score, brightness, 0.0 

    # --- B. 미적 평가 (CLIP) ---
    def get_aesthetic_score(self, image_path):
        img_pil = Image.open(image_path)
        prompts = ["high quality, professional, aesthetic", "low quality, blurry, ugly"]
        
        inputs = self.processor(text=prompts, images=img_pil, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)
        
        return probs[0][0].item() * 100

    # --- C. 최종 점수 계산 로직 ---
    def calculate_final_score(self, blur, brightness, brisque_val, aesthetic_score):
        
        # 1. Laplacian 정규화 (0-100점)
        laplacian_norm = min(100, blur / (self.LAPLACIAN_MAX / 100)) 

        # 2. 기술 점수(T-Score) = Laplacian 점수 (단순화)
        T_score = laplacian_norm 

        # 3. 밝기 페널티 적용
        penalty = 0.0
        if brightness < self.BRIGHT_LOWER or brightness > self.BRIGHT_UPPER:
            penalty = 0.5 
        T_score *= (1 - penalty)

        # 4. 최종 합산
        final_score = (aesthetic_score * self.W_AESTHETIC) + (T_score * self.W_TECHNICAL)
        
        return {
            "final_score": round(final_score, 2),
            "aesthetic": round(aesthetic_score, 2),
            "technical": round(T_score, 2),
            "raw_metrics": {
                "raw_laplacian": round(blur, 1),
                "raw_brisque": 0.0, # BRISQUE는 0.0으로 고정
                "raw_brightness": round(brightness, 1)
            },
            "penalty_applied": penalty > 0,
        }
    
    def analyze_image(self, image_path):
        """외부에서 호출되는 메인 분석 함수"""
        blur, bright, brisque_val = self.get_technical_metrics(image_path)
        aesthetic_score = self.get_aesthetic_score(image_path)
        return self.calculate_final_score(blur, bright, brisque_val, aesthetic_score)