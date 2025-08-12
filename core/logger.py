"""
로깅 시스템 관리 모듈
"""
import logging
import os
from typing import List


class LogCaptureHandler(logging.Handler):
    """로그를 캡처하는 커스텀 핸들러"""
    
    def __init__(self, log_buffer: List[str], max_logs: int):
        super().__init__()
        self.log_buffer = log_buffer
        self.max_logs = max_logs
    
    def emit(self, record):
        try:
            # 로그 메시지 포맷팅
            msg = self.format(record)
            
            # 로그 레벨에 따른 이모지 추가
            level_emoji = {
                'DEBUG': '🔍',
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            
            emoji = level_emoji.get(record.levelname, 'ℹ️')
            formatted_msg = f"{emoji} {msg}"
            
            # 버퍼에 추가
            self.log_buffer.append(formatted_msg)
            
            # 최대 개수 제한
            if len(self.log_buffer) > self.max_logs:
                self.log_buffer.pop(0)
                
        except Exception:
            pass


class Logger:
    """로깅 설정을 관리하는 클래스"""
    
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        self.logger = logging.getLogger("econ-analyzer")
        _log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        try:
            self.logger.setLevel(_log_level)
        except Exception:
            self.logger.setLevel(logging.INFO)
        
        # 로그 캡처를 위한 리스트
        self.log_buffer = []
        self.max_logs = 100  # 최대 로그 개수
        
        # 커스텀 핸들러 추가
        self.handler = LogCaptureHandler(self.log_buffer, self.max_logs)
        self.logger.addHandler(self.handler)
    
    def info(self, message, *args):
        self.logger.info(message, *args)
    
    def warning(self, message, *args):
        self.logger.warning(message, *args)
    
    def error(self, message, *args):
        self.logger.error(message, *args)
    
    def exception(self, message, *args):
        self.logger.exception(message, *args)
    
    def debug(self, message, *args):
        self.logger.debug(message, *args)
    
    def get_recent_logs(self, count: int = 20) -> List[str]:
        """최근 로그들을 반환합니다."""
        return self.log_buffer[-count:] if self.log_buffer else []
    
    def clear_logs(self):
        """로그 버퍼를 클리어합니다."""
        self.log_buffer.clear()


# 전역 로거 인스턴스
logger = Logger() 