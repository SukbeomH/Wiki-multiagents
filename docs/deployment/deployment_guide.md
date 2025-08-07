# 배포 가이드

## 📋 개요

AI Knowledge Graph System의 배포 방법을 설명합니다. 로컬 개발 환경부터 프로덕션 배포까지 다양한 환경에서의 배포 방법을 다룹니다.

## 🏗️ 배포 아키텍처

### 전체 구성도
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   FastAPI       │    │   Streamlit     │
│   (Nginx)       │────│   Backend       │────│   Frontend      │
│   Port 80/443   │    │   Port 8000     │    │   Port 8501     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────┤   Storage       │──────────────┘
                        │   Layer         │
                        └─────────────────┘
                                 │
    ┌─────────────────────────────┼─────────────────────────────┐
    │                             │                             │
┌───▼──────┐              ┌──────▼──────┐              ┌───────▼────┐
│   Cache  │              │   Vector    │              │   Knowledge│
│   (Disk) │              │   Store     │              │   Graph    │
│   ./data │              │   (FAISS)   │              │   (RDFLib) │
└──────────┘              └─────────────┘              └────────────┘
```

## 🐳 Docker 배포 (권장)

### 1. 로컬 Docker 배포

#### 기본 배포
```bash
# 1. 리포지토리 클론
git clone <repository-url>
cd aibootcamp-final

# 2. 환경변수 설정
cp config/environment.template .env
# .env 파일 편집

# 3. Docker Compose로 배포
docker-compose up -d

# 4. 서비스 확인
docker-compose ps
```

#### 개발 환경 배포
```bash
# 개발 도구 포함 배포
docker-compose --profile dev up -d

# 추가 서비스:
# - Redis Commander (포트 8081)
# - Neo4j Browser (포트 7474)
# - Grafana (포트 3000)
```

### 2. 프로덕션 Docker 배포

#### 프로덕션 설정
```bash
# 프로덕션 환경변수 설정
export NODE_ENV=production
export DEBUG=false
export LOG_LEVEL=WARNING

# 프로덕션 배포
docker-compose -f docker-compose.prod.yml up -d
```

#### 프로덕션 Docker Compose 예시
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - fastapi
      - streamlit

  fastapi:
    build: 
      context: ./server
      dockerfile: Dockerfile.prod
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=WARNING
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  streamlit:
    build:
      context: ./app
      dockerfile: Dockerfile.prod
    environment:
      - NODE_ENV=production
    restart: unless-stopped
```

## ☁️ 클라우드 배포

### 1. AWS 배포 (Terraform)

#### 인프라 배포
```bash
# 1. AWS 인증 설정
aws configure

# 2. Terraform 초기화
cd infra/terraform
terraform init

# 3. 인프라 배포
terraform plan
terraform apply

# 4. 애플리케이션 배포
cd ../scripts
./deploy.sh
```

#### Terraform 구성 요소
- **EC2 Instance**: t3.large (2 vCPU, 8GB RAM)
- **VPC**: 프라이빗/퍼블릭 서브넷
- **Security Groups**: 포트 22, 80, 443, 8000, 8501
- **EBS Volume**: 50GB 데이터 저장용
- **Elastic IP**: 고정 공인 IP

### 2. Google Cloud Platform 배포

#### GKE (Kubernetes) 배포
```bash
# 1. GKE 클러스터 생성
gcloud container clusters create ai-kg-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=e2-standard-2

# 2. kubectl 설정
gcloud container clusters get-credentials ai-kg-cluster --zone=us-central1-a

# 3. Kubernetes 매니페스트 배포
kubectl apply -f k8s/
```

#### Kubernetes 매니페스트 예시
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-kg-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-kg-backend
  template:
    metadata:
      labels:
        app: ai-kg-backend
    spec:
      containers:
      - name: fastapi
        image: ai-kg-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: AZURE_OPENAI_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: endpoint
```

### 3. Azure 배포

#### Azure Container Instances
```bash
# 1. Azure CLI 로그인
az login

# 2. 리소스 그룹 생성
az group create --name ai-kg-rg --location eastus

# 3. 컨테이너 인스턴스 배포
az container create \
  --resource-group ai-kg-rg \
  --name ai-kg-backend \
  --image ai-kg-backend:latest \
  --ports 8000 \
  --environment-variables \
    AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
    AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY
```

## 🔧 환경별 설정

### 1. 개발 환경

#### 환경변수
```bash
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG
AZURE_OPENAI_ENDPOINT=https://dev-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=dev_api_key
AZURE_OPENAI_DEPLOY_GPT4O=dev-gpt4o
CACHE_MAX_SIZE=536870912  # 512MB
```

#### Docker Compose
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  fastapi:
    build: ./server
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
    volumes:
      - ./server:/app
      - ./data:/app/data
    command: uvicorn main:app --reload --host 0.0.0.0

  streamlit:
    build: ./app
    ports:
      - "8501:8501"
    environment:
      - DEBUG=true
    volumes:
      - ./app:/app
```

### 2. 스테이징 환경

#### 환경변수
```bash
# .env.staging
DEBUG=false
LOG_LEVEL=INFO
AZURE_OPENAI_ENDPOINT=https://staging-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=staging_api_key
AZURE_OPENAI_DEPLOY_GPT4O=staging-gpt4o
CACHE_MAX_SIZE=1073741824  # 1GB
```

### 3. 프로덕션 환경

#### 환경변수
```bash
# .env.production
DEBUG=false
LOG_LEVEL=WARNING
AZURE_OPENAI_ENDPOINT=https://prod-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=prod_api_key
AZURE_OPENAI_DEPLOY_GPT4O=prod-gpt4o
CACHE_MAX_SIZE=2147483648  # 2GB
```

## 📊 모니터링 및 로깅

### 1. 로깅 설정

#### 구조화된 로깅
```python
# logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        return json.dumps(log_entry)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### 2. 헬스체크

#### 헬스체크 엔드포인트
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "healthy",
            "cache": await cache_manager.health_check(),
            "vector_store": await vector_store.health_check()
        }
    }
```

### 3. 메트릭 수집

#### Prometheus 메트릭
```python
from prometheus_client import Counter, Histogram, generate_latest

# 메트릭 정의
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🔒 보안 설정

### 1. SSL/TLS 설정

#### Nginx SSL 설정
```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://streamlit:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/ {
        proxy_pass http://fastapi:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 방화벽 설정

#### UFW 설정 (Ubuntu)
```bash
# 기본 정책 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH 허용
sudo ufw allow ssh

# 웹 서비스 허용
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8501/tcp

# 방화벽 활성화
sudo ufw enable
```

### 3. 환경변수 보안

#### 시크릿 관리
```bash
# Docker Secrets 사용
echo "your-secret-value" | docker secret create azure_openai_key -

# Kubernetes Secrets
kubectl create secret generic azure-secrets \
  --from-literal=endpoint=$AZURE_OPENAI_ENDPOINT \
  --from-literal=api-key=$AZURE_OPENAI_API_KEY
```

## 🚀 배포 자동화

### 1. GitHub Actions CI/CD

#### 워크플로우 예시
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker images
      run: |
        docker build -t ai-kg-backend:${{ github.sha }} ./server
        docker build -t ai-kg-frontend:${{ github.sha }} ./app
    
    - name: Deploy to AWS
      run: |
        aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
        docker tag ai-kg-backend:${{ github.sha }} ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/ai-kg-backend:latest
        docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/ai-kg-backend:latest
    
    - name: Update ECS service
      run: |
        aws ecs update-service --cluster ai-kg-cluster --service ai-kg-service --force-new-deployment
```

### 2. 배포 스크립트

#### 배포 스크립트 예시
```bash
#!/bin/bash
# deploy.sh

set -e

# 환경 확인
if [ -z "$ENVIRONMENT" ]; then
    echo "ENVIRONMENT 변수를 설정하세요 (dev/staging/prod)"
    exit 1
fi

# 백업 생성
echo "백업 생성 중..."
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz ./data

# 새 버전 배포
echo "새 버전 배포 중..."
docker-compose -f docker-compose.${ENVIRONMENT}.yml pull
docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d

# 헬스체크
echo "헬스체크 중..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "배포 성공!"
        exit 0
    fi
    sleep 2
done

echo "배포 실패: 헬스체크 타임아웃"
exit 1
```

## 📈 성능 최적화

### 1. 리소스 요구사항

#### 최소 요구사항
- **CPU**: 2 vCPU
- **메모리**: 8GB RAM
- **디스크**: 50GB SSD
- **네트워크**: 100Mbps

#### 권장 요구사항
- **CPU**: 4 vCPU
- **메모리**: 16GB RAM
- **디스크**: 100GB SSD
- **네트워크**: 1Gbps

### 2. 스케일링 전략

#### 수평 스케일링
```yaml
# docker-compose.scale.yml
services:
  fastapi:
    deploy:
      replicas: 3
    environment:
      - WORKER_PROCESSES=4
  
  streamlit:
    deploy:
      replicas: 2
```

#### 로드 밸런싱
```nginx
# nginx.conf
upstream fastapi_backend {
    least_conn;
    server fastapi1:8000;
    server fastapi2:8000;
    server fastapi3:8000;
}

server {
    location /api/ {
        proxy_pass http://fastapi_backend;
    }
}
```

## 🛠️ 문제 해결

### 일반적인 배포 문제

#### 1. 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep :8000
lsof -i :8501

# 프로세스 종료
kill -9 <PID>
```

#### 2. 메모리 부족
```bash
# 메모리 사용량 확인
free -h
docker stats

# 불필요한 컨테이너 정리
docker container prune
docker image prune
```

#### 3. 디스크 공간 부족
```bash
# 디스크 사용량 확인
df -h
du -sh ./data/*

# 로그 파일 정리
find ./logs -name "*.log" -mtime +7 -delete
```

### 로그 분석

#### 로그 모니터링
```bash
# 실시간 로그 확인
docker-compose logs -f fastapi

# 에러 로그 필터링
docker-compose logs fastapi | grep ERROR

# 특정 시간대 로그
docker-compose logs --since="2025-08-07T10:00:00" fastapi
```

## 📚 추가 리소스

- **Docker 문서**: https://docs.docker.com/
- **Kubernetes 문서**: https://kubernetes.io/docs/
- **Terraform 문서**: https://www.terraform.io/docs/
- **Nginx 문서**: https://nginx.org/en/docs/
- **Prometheus 문서**: https://prometheus.io/docs/

---

*마지막 업데이트: 2025-08-07* 