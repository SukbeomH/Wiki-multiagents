"""
Redis 마이그레이션 성능 벤치마크

Redis vs diskcache 성능 비교 및 벤치마크 테스트
"""

import time
import statistics
import asyncio
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

from server.utils.storage_manager import StorageManager
from server.utils.cache_manager import CacheManager, CacheConfig
from server.utils.lock_manager import DistributedLockManager
from server.schemas.base import CheckpointData, CheckpointType, WorkflowState, WorkflowStage


@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    operation: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    operations_per_second: float
    success_rate: float


class RedisMigrationBenchmark:
    """Redis 마이그레이션 벤치마크"""
    
    def __init__(self, temp_dir: str = None):
        self.temp_dir = temp_dir or tempfile.mkdtemp()
        self.results: List[BenchmarkResult] = []
        self.setup_storage()
    
    def setup_storage(self):
        """스토리지 시스템 설정"""
        import os
        
        # 환경변수 설정
        os.environ.update({
            "CACHE_DIR": f"{self.temp_dir}/cache",
            "LOCK_DIR": f"{self.temp_dir}/locks",
            "CACHE_MAX_SIZE": str(100 * 1024 * 1024),  # 100MB
            "CACHE_DEFAULT_TTL": "3600",  # 1시간
            "CACHE_CHECKPOINT_TTL": "86400"  # 24시간
        })
        
        self.storage_manager = StorageManager()
        print(f"✅ 벤치마크 환경 설정 완료: {self.temp_dir}")
    
    def cleanup(self):
        """정리"""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"🧹 벤치마크 환경 정리 완료")
        except Exception as e:
            print(f"⚠️ 정리 중 오류: {e}")
    
    def measure_time(self, func, *args, **kwargs) -> tuple:
        """실행 시간 측정"""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            print(f"❌ 오류 발생: {e}")
        
        end_time = time.time()
        return end_time - start_time, success, result
    
    def benchmark_cache_operations(self, iterations: int = 1000):
        """캐시 작업 벤치마크"""
        print(f"\n🚀 캐시 작업 벤치마크 시작 ({iterations}회)")
        
        # 기본 Set/Get 벤치마크
        set_times = []
        get_times = []
        successful_operations = 0
        
        for i in range(iterations):
            key = f"benchmark_key_{i}"
            value = f"benchmark_value_{i}_{'x' * 100}"  # ~100자 데이터
            
            # Set 성능 측정
            set_time, success, _ = self.measure_time(
                self.storage_manager.cache_manager.set, key, value
            )
            set_times.append(set_time)
            
            if success:
                # Get 성능 측정
                get_time, success, retrieved = self.measure_time(
                    self.storage_manager.cache_manager.get, key
                )
                get_times.append(get_time)
                
                if success and retrieved == value:
                    successful_operations += 1
        
        # Set 결과 저장
        self.results.append(BenchmarkResult(
            operation="Cache Set",
            iterations=iterations,
            total_time=sum(set_times),
            avg_time=statistics.mean(set_times),
            min_time=min(set_times),
            max_time=max(set_times),
            median_time=statistics.median(set_times),
            operations_per_second=iterations / sum(set_times),
            success_rate=successful_operations / iterations
        ))
        
        # Get 결과 저장
        self.results.append(BenchmarkResult(
            operation="Cache Get",
            iterations=iterations,
            total_time=sum(get_times),
            avg_time=statistics.mean(get_times),
            min_time=min(get_times),
            max_time=max(get_times),
            median_time=statistics.median(get_times),
            operations_per_second=iterations / sum(get_times),
            success_rate=successful_operations / iterations
        ))
        
        print(f"✅ 캐시 Set: {iterations / sum(set_times):.2f} ops/sec")
        print(f"✅ 캐시 Get: {iterations / sum(get_times):.2f} ops/sec")
    
    def benchmark_json_operations(self, iterations: int = 500):
        """JSON 작업 벤치마크"""
        print(f"\n🚀 JSON 작업 벤치마크 시작 ({iterations}회)")
        
        json_set_times = []
        json_get_times = []
        successful_operations = 0
        
        for i in range(iterations):
            key = f"json_benchmark_{i}"
            json_data = {
                "id": i,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "items": [f"item_{j}" for j in range(10)],
                    "metadata": {
                        "type": "benchmark",
                        "iteration": i,
                        "size": "medium"
                    }
                },
                "status": "active"
            }
            
            # JSON Set 성능 측정
            set_time, success, _ = self.measure_time(
                self.storage_manager.cache_manager.json_set, key, "$", json_data
            )
            json_set_times.append(set_time)
            
            if success:
                # JSON Get 성능 측정
                get_time, success, retrieved = self.measure_time(
                    self.storage_manager.cache_manager.json_get, key, "$"
                )
                json_get_times.append(get_time)
                
                if success and retrieved == json_data:
                    successful_operations += 1
        
        # JSON Set 결과
        self.results.append(BenchmarkResult(
            operation="JSON Set",
            iterations=iterations,
            total_time=sum(json_set_times),
            avg_time=statistics.mean(json_set_times),
            min_time=min(json_set_times),
            max_time=max(json_set_times),
            median_time=statistics.median(json_set_times),
            operations_per_second=iterations / sum(json_set_times),
            success_rate=successful_operations / iterations
        ))
        
        # JSON Get 결과
        self.results.append(BenchmarkResult(
            operation="JSON Get",
            iterations=iterations,
            total_time=sum(json_get_times),
            avg_time=statistics.mean(json_get_times),
            min_time=min(json_get_times),
            max_time=max(json_get_times),
            median_time=statistics.median(json_get_times),
            operations_per_second=iterations / sum(json_get_times),
            success_rate=successful_operations / iterations
        ))
        
        print(f"✅ JSON Set: {iterations / sum(json_set_times):.2f} ops/sec")
        print(f"✅ JSON Get: {iterations / sum(json_get_times):.2f} ops/sec")
    
    def benchmark_lock_operations(self, iterations: int = 200):
        """락 작업 벤치마크"""
        print(f"\n🚀 락 작업 벤치마크 시작 ({iterations}회)")
        
        acquire_times = []
        release_times = []
        successful_operations = 0
        
        for i in range(iterations):
            resource = f"benchmark_lock_{i}"
            
            # 락 획득 성능 측정
            acquire_time, success, lock_id = self.measure_time(
                self.storage_manager.acquire_lock_sync, resource, 5, 1.0
            )
            acquire_times.append(acquire_time)
            
            if success and lock_id:
                # 락 해제 성능 측정
                release_time, success, _ = self.measure_time(
                    self.storage_manager.release_lock, resource, lock_id
                )
                release_times.append(release_time)
                
                if success:
                    successful_operations += 1
        
        # 락 획득 결과
        self.results.append(BenchmarkResult(
            operation="Lock Acquire",
            iterations=iterations,
            total_time=sum(acquire_times),
            avg_time=statistics.mean(acquire_times),
            min_time=min(acquire_times),
            max_time=max(acquire_times),
            median_time=statistics.median(acquire_times),
            operations_per_second=iterations / sum(acquire_times),
            success_rate=successful_operations / iterations
        ))
        
        # 락 해제 결과
        if release_times:
            self.results.append(BenchmarkResult(
                operation="Lock Release",
                iterations=len(release_times),
                total_time=sum(release_times),
                avg_time=statistics.mean(release_times),
                min_time=min(release_times),
                max_time=max(release_times),
                median_time=statistics.median(release_times),
                operations_per_second=len(release_times) / sum(release_times),
                success_rate=successful_operations / iterations
            ))
        
        print(f"✅ 락 Acquire: {iterations / sum(acquire_times):.2f} ops/sec")
        if release_times:
            print(f"✅ 락 Release: {len(release_times) / sum(release_times):.2f} ops/sec")
    
    def benchmark_checkpoint_operations(self, iterations: int = 100):
        """체크포인트 작업 벤치마크"""
        print(f"\n🚀 체크포인트 작업 벤치마크 시작 ({iterations}회)")
        
        save_times = []
        load_times = []
        successful_operations = 0
        
        for i in range(iterations):
            workflow_id = f"benchmark_workflow_{i}"
            
            # WorkflowState 생성
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                trace_id=f"benchmark_trace_{i}",
                current_stage=WorkflowStage.RESEARCH,
                keyword=f"benchmark test {i}"
            )
            
            # CheckpointData 생성
            checkpoint_data = CheckpointData(
                workflow_id=workflow_id,
                checkpoint_type=CheckpointType.PERIODIC,
                state_snapshot=workflow_state
            )
            
            # 체크포인트 저장 성능 측정
            save_time, success, checkpoint_key = self.measure_time(
                self.storage_manager.save_checkpoint, checkpoint_data
            )
            save_times.append(save_time)
            
            if success and checkpoint_key:
                # 체크포인트 로드 성능 측정
                load_time, success, loaded = self.measure_time(
                    self.storage_manager.load_checkpoint, workflow_id
                )
                load_times.append(load_time)
                
                if success and loaded and loaded.workflow_id == workflow_id:
                    successful_operations += 1
        
        # 체크포인트 저장 결과
        self.results.append(BenchmarkResult(
            operation="Checkpoint Save",
            iterations=iterations,
            total_time=sum(save_times),
            avg_time=statistics.mean(save_times),
            min_time=min(save_times),
            max_time=max(save_times),
            median_time=statistics.median(save_times),
            operations_per_second=iterations / sum(save_times),
            success_rate=successful_operations / iterations
        ))
        
        # 체크포인트 로드 결과
        if load_times:
            self.results.append(BenchmarkResult(
                operation="Checkpoint Load",
                iterations=len(load_times),
                total_time=sum(load_times),
                avg_time=statistics.mean(load_times),
                min_time=min(load_times),
                max_time=max(load_times),
                median_time=statistics.median(load_times),
                operations_per_second=len(load_times) / sum(load_times),
                success_rate=successful_operations / iterations
            ))
        
        print(f"✅ 체크포인트 Save: {iterations / sum(save_times):.2f} ops/sec")
        if load_times:
            print(f"✅ 체크포인트 Load: {len(load_times) / sum(load_times):.2f} ops/sec")
    
    def benchmark_concurrent_operations(self, workers: int = 5, operations_per_worker: int = 50):
        """동시성 작업 벤치마크"""
        print(f"\n🚀 동시성 작업 벤치마크 시작 ({workers} 워커, 각 {operations_per_worker}회)")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        start_time = time.time()
        
        def worker_task(worker_id):
            """워커 작업"""
            worker_times = []
            successful_ops = 0
            
            for i in range(operations_per_worker):
                resource = f"concurrent_test_{worker_id}_{i}"
                
                # 락 획득/해제 사이클
                op_start = time.time()
                
                with self.storage_manager.acquire_lock(resource, ttl=1) as lock_id:
                    if lock_id:
                        # 캐시 작업
                        key = f"worker_{worker_id}_data_{i}"
                        data = {"worker": worker_id, "operation": i, "timestamp": time.time()}
                        
                        self.storage_manager.cache_manager.json_set(key, "$", data)
                        retrieved = self.storage_manager.cache_manager.json_get(key, "$")
                        
                        if retrieved == data:
                            successful_ops += 1
                
                worker_times.append(time.time() - op_start)
            
            results_queue.put((worker_id, worker_times, successful_ops))
        
        # 워커 스레드 시작
        threads = []
        for worker_id in range(workers):
            thread = threading.Thread(target=worker_task, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 수집
        total_time = time.time() - start_time
        all_times = []
        total_successful = 0
        
        while not results_queue.empty():
            worker_id, times, successful = results_queue.get()
            all_times.extend(times)
            total_successful += successful
        
        total_operations = workers * operations_per_worker
        
        # 동시성 결과
        self.results.append(BenchmarkResult(
            operation="Concurrent Operations",
            iterations=total_operations,
            total_time=total_time,
            avg_time=statistics.mean(all_times),
            min_time=min(all_times),
            max_time=max(all_times),
            median_time=statistics.median(all_times),
            operations_per_second=total_operations / total_time,
            success_rate=total_successful / total_operations
        ))
        
        print(f"✅ 동시성 작업: {total_operations / total_time:.2f} ops/sec")
        print(f"✅ 성공률: {(total_successful / total_operations) * 100:.1f}%")
    
    def generate_report(self) -> Dict[str, Any]:
        """벤치마크 보고서 생성"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "backend": "diskcache + filelock",
                "temp_dir": self.temp_dir,
                "storage_type": "local_filesystem"
            },
            "benchmark_results": [],
            "summary": {}
        }
        
        # 개별 결과 추가
        for result in self.results:
            report["benchmark_results"].append({
                "operation": result.operation,
                "iterations": result.iterations,
                "total_time": round(result.total_time, 4),
                "avg_time": round(result.avg_time, 6),
                "min_time": round(result.min_time, 6),
                "max_time": round(result.max_time, 6),
                "median_time": round(result.median_time, 6),
                "operations_per_second": round(result.operations_per_second, 2),
                "success_rate": round(result.success_rate, 4)
            })
        
        # 요약 통계
        if self.results:
            total_operations = sum(r.iterations for r in self.results)
            total_time = sum(r.total_time for r in self.results)
            avg_ops_per_sec = statistics.mean([r.operations_per_second for r in self.results])
            avg_success_rate = statistics.mean([r.success_rate for r in self.results])
            
            report["summary"] = {
                "total_operations": total_operations,
                "total_time": round(total_time, 4),
                "average_ops_per_second": round(avg_ops_per_sec, 2),
                "average_success_rate": round(avg_success_rate, 4),
                "fastest_operation": max(self.results, key=lambda r: r.operations_per_second).operation,
                "slowest_operation": min(self.results, key=lambda r: r.operations_per_second).operation
            }
        
        return report
    
    def print_report(self):
        """보고서 출력"""
        print("\n" + "="*80)
        print("🏆 Redis 마이그레이션 성능 벤치마크 보고서")
        print("="*80)
        
        if not self.results:
            print("❌ 벤치마크 결과가 없습니다.")
            return
        
        print(f"\n📊 시스템 정보:")
        print(f"   백엔드: diskcache + filelock")
        print(f"   저장소: {self.temp_dir}")
        print(f"   날짜: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n📈 벤치마크 결과:")
        print("-"*80)
        print(f"{'작업':<20} {'횟수':<8} {'총 시간':<10} {'평균':<12} {'ops/sec':<12} {'성공률':<8}")
        print("-"*80)
        
        for result in self.results:
            print(f"{result.operation:<20} "
                  f"{result.iterations:<8} "
                  f"{result.total_time:<10.4f} "
                  f"{result.avg_time:<12.6f} "
                  f"{result.operations_per_second:<12.2f} "
                  f"{result.success_rate:<8.4f}")
        
        # 요약
        total_ops = sum(r.iterations for r in self.results)
        total_time = sum(r.total_time for r in self.results)
        avg_ops_per_sec = statistics.mean([r.operations_per_second for r in self.results])
        
        print("-"*80)
        print(f"📋 요약:")
        print(f"   총 작업 수: {total_ops:,}")
        print(f"   총 실행 시간: {total_time:.4f}초")
        print(f"   평균 처리량: {avg_ops_per_sec:.2f} ops/sec")
        print(f"   가장 빠른 작업: {max(self.results, key=lambda r: r.operations_per_second).operation}")
        print(f"   가장 느린 작업: {min(self.results, key=lambda r: r.operations_per_second).operation}")
        print("="*80)
    
    def save_report(self, filename: str = None):
        """보고서 파일 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"redis_migration_benchmark_{timestamp}.json"
        
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"💾 벤치마크 보고서 저장: {filename}")
        return filename


def run_full_benchmark():
    """전체 벤치마크 실행"""
    print("🚀 Redis 마이그레이션 성능 벤치마크 시작")
    print("="*80)
    
    benchmark = RedisMigrationBenchmark()
    
    try:
        # 각종 벤치마크 실행
        benchmark.benchmark_cache_operations(iterations=1000)
        benchmark.benchmark_json_operations(iterations=500)
        benchmark.benchmark_lock_operations(iterations=200)
        benchmark.benchmark_checkpoint_operations(iterations=100)
        benchmark.benchmark_concurrent_operations(workers=5, operations_per_worker=50)
        
        # 결과 출력 및 저장
        benchmark.print_report()
        report_file = benchmark.save_report()
        
        print(f"\n✅ 벤치마크 완료! 보고서: {report_file}")
        
    except Exception as e:
        print(f"❌ 벤치마크 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    run_full_benchmark()