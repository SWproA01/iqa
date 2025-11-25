import cv2
import numpy as np
import torch
import math
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io

# BRISQUE 계산을 위해 piq 라이브러리 사용
# piq 설치 필요: pip install piq
from piq import brisque 

class HybridScorer:
    """
    CLIP 미적 점수와 Laplacian/BRISQUE 기술 점수를 합산하여 최종 이미지 점수를 계산하는 클래스.
    """
    def __init__(self, device='cpu'):
        # 1. 최종 점수 가중치 (총합 1.0)
        self.W_AESTHETIC = 0.65      # 미적 점수 가중치 (CLIP)
        self.W_TECHNICAL = 0.35      # 기술 점수 가중치 (Laplacian + BRISQUE)
        
        # 2. 기술 점수 내부 가중치 (총합 1.0)
        # T_score = (W_T_LAP * Laplacian_Score) + (W_T_BRISQUE * BRISQUE_Score)
        self.W_T_LAPLACIAN = 0.6     # Laplacian 중요도 (선명도)
        self.W_T_BRISQUE = 0.4       # BRISQUE 중요도 (일반적 품질)
        
        # 3. 정규화 및 밝기 기준
        self.LAPLACIAN_MAX = 1000.0  # Laplacian 정규화 기준
        self.BRIGHT_LOWER = 30.0
        self.BRIGHT_UPPER = 220.0
        
        # 4. CLIP 모델 로드
        self.device = device
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        print(f"HybridScorer 초기화 완료. Device: {self.device}")

    # --- A. 기술적 지표 추출 ---
    def get_technical_metrics(self, image_path):
        """Laplacian, 밝기, BRISQUE 값을 계산합니다."""
        
        # 1. 파일 읽기 및 OpenCV 로드
        with open(image_path, 'rb') as f:
            img_bytes = f.read()

        np_array = np.frombuffer(img_bytes, np.uint8)
        img_cv = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if img_cv is None:
            raise FileNotFoundError("OpenCV 디코딩 실패. 이미지 경로를 확인하거나 파일이 손상되지 않았는지 확인하세요.")

        target_width = 640
        h, w, _ = img_cv.shape
        scale = target_width / w
        new_h = int(h * scale)
        img_resized = cv2.resize(img_cv, (target_width, new_h), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var() 
        brightness = np.mean(gray)
        
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        img_tensor = torch.tensor(img_rgb, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0
        img_tensor = img_tensor.to(self.device)
        
        brisque_val = 0.0
        try:
            brisque_val = brisque(img_tensor, data_range=1.0, reduction='mean').item()
        except Exception as e:
            print(f"BRISQUE 계산 오류: {e}. BRISQUE 점수를 0.0으로 설정합니다.")
            
        return blur_score, brightness, brisque_val 

    # --- B. 미적 평가 (CLIP) ---
    def get_aesthetic_score(self, image_path):
        """CLIP 모델을 사용하여 미적 점수(0-100)를 계산합니다."""
        img_pil = Image.open(image_path).convert('RGB')
        # CLIP을 사용하여 이미지 품질과 미적 가치를 평가하는 프롬프트
        prompts = ["high quality, professional, aesthetic", "low quality, blurry, ugly"]
        
        inputs = self.processor(text=prompts, images=img_pil, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Logits를 Softmax하여 확률로 변환
            probs = outputs.logits_per_image.softmax(dim=1)
        
        # 첫 번째 프롬프트("high quality...")의 확률을 100점 만점으로 변환
        return probs[0][0].item() * 100

    # --- C. 최종 점수 계산 로직 ---
    def calculate_final_score(self, blur, brightness, brisque_val, aesthetic_score):
        """기술 지표를 합산하고 미적 점수와 가중치를 적용하여 최종 점수를 계산합니다."""
        
        # 1. Laplacian 정규화 (0-100점) - 높을수록 좋음
        laplacian_norm = min(100.0, blur / (self.LAPLACIAN_MAX / 100.0)) 

        # 2. BRISQUE 점수 변환 및 정규화 (0-100점)
        # BRISQUE는 낮을수록 좋음 (0이 최고 품질). 100 - BRISQUE를 사용하여 높을수록 좋은 점수로 변환
        brisque_score_converted = max(0.0, 100.0 - min(100.0, brisque_val))

        # 3. 기술 점수(T-Score) - Laplacian과 BRISQUE의 가중 합산
        T_score = (laplacian_norm * self.W_T_LAPLACIAN) + \
                  (brisque_score_converted * self.W_T_BRISQUE)
        
        # 4. 밝기 페널티 적용
        penalty = 0.0
        if brightness < self.BRIGHT_LOWER or brightness > self.BRIGHT_UPPER:
            # 밝기 기준을 벗어나면 50% 감점 적용
            penalty = 0.5 
        
        T_score *= (1.0 - penalty)
        T_score = round(T_score, 2)

        # 5. 최종 합산
        final_score = (aesthetic_score * self.W_AESTHETIC) + (T_score * self.W_TECHNICAL)
        
        return {
            "final_score": round(final_score, 2),
            "aesthetic": round(aesthetic_score, 2),
            "technical": T_score,
            "raw_metrics": {
                "raw_laplacian": round(blur, 1),
                "raw_brisque": round(brisque_val, 1), 
                "raw_brightness": round(brightness, 1)
            },
            "penalty_applied": penalty > 0.0,
        }
    
    def analyze_image(self, image_path):
        """외부에서 호출되는 메인 분석 함수: 기술 지표와 미적 점수를 계산하고 최종 점수를 반환합니다."""
        blur, bright, brisque_val = self.get_technical_metrics(image_path)
        aesthetic_score = self.get_aesthetic_score(image_path)
        return self.calculate_final_score(blur, bright, brisque_val, aesthetic_score)