"""
本番環境移行前のパフォーマンステスト
"""
import time
import requests
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
from database import SessionLocal
from services import calculate_weekly_points_logic
import json

class PerformanceTester:
    """パフォーマンステストクラス"""
    
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.results = []
    
    def test_endpoint_response_time(self, endpoint, method="GET", data=None, num_requests=10):
        """エンドポイントのレスポンス時間をテスト"""
        response_times = []
        errors = 0
        
        for i in range(num_requests):
            start_time = time.time()
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                elif method == "POST":
                    response = requests.post(f"{self.base_url}{endpoint}", data=data, timeout=10)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ミリ秒
                
                if response.status_code == 200:
                    response_times.append(response_time)
                else:
                    errors += 1
                    
            except Exception as e:
                errors += 1
                print(f"Request {i+1} failed: {e}")
        
        if response_times:
            return {
                'endpoint': endpoint,
                'method': method,
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'median_response_time': statistics.median(response_times),
                'success_rate': (num_requests - errors) / num_requests * 100,
                'total_requests': num_requests,
                'errors': errors
            }
        else:
            return {
                'endpoint': endpoint,
                'error': 'All requests failed',
                'errors': errors
            }
    
    def test_concurrent_load(self, endpoint, concurrent_users=5, requests_per_user=10):
        """同時アクセス負荷テスト"""
        def user_session():
            user_results = []
            for _ in range(requests_per_user):
                start_time = time.time()
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    end_time = time.time()
                    user_results.append({
                        'response_time': (end_time - start_time) * 1000,
                        'status_code': response.status_code,
                        'success': response.status_code == 200
                    })
                except Exception as e:
                    user_results.append({
                        'error': str(e),
                        'success': False
                    })
            return user_results
        
        # 並行実行
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_session) for _ in range(concurrent_users)]
            all_results = []
            for future in futures:
                all_results.extend(future.result())
        
        # 結果分析
        successful_requests = [r for r in all_results if r.get('success', False)]
        failed_requests = len(all_results) - len(successful_requests)
        
        if successful_requests:
            response_times = [r['response_time'] for r in successful_requests]
            return {
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'requests_per_user': requests_per_user,
                'total_requests': len(all_results),
                'successful_requests': len(successful_requests),
                'failed_requests': failed_requests,
                'success_rate': len(successful_requests) / len(all_results) * 100,
                'avg_response_time': statistics.mean(response_times),
                'max_response_time': max(response_times),
                'min_response_time': min(response_times)
            }
    
    def test_database_performance(self, num_tests=100):
        """データベースパフォーマンステスト"""
        db = SessionLocal()
        response_times = []
        
        try:
            for _ in range(num_tests):
                start_time = time.time()
                
                # 典型的なデータベース操作をテスト
                result = calculate_weekly_points_logic(db, 1)  # ユーザーID 1でテスト
                
                end_time = time.time()
                response_times.append((end_time - start_time) * 1000)
        
        finally:
            db.close()
        
        return {
            'test_type': 'database_performance',
            'num_tests': num_tests,
            'avg_response_time': statistics.mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'median_response_time': statistics.median(response_times)
        }
    
    def run_full_performance_test(self):
        """包括的なパフォーマンステスト"""
        print("=== パフォーマンステスト開始 ===\n")
        
        # エンドポイントテスト
        endpoints_to_test = [
            {'endpoint': '/', 'method': 'GET'},
            {'endpoint': '/login', 'method': 'GET'},
            {'endpoint': '/points', 'method': 'GET'},
        ]
        
        for test_config in endpoints_to_test:
            print(f"Testing {test_config['endpoint']}...")
            result = self.test_endpoint_response_time(**test_config)
            self.results.append(result)
            
            if 'error' not in result:
                print(f"  平均レスポンス時間: {result['avg_response_time']:.2f}ms")
                print(f"  成功率: {result['success_rate']:.1f}%")
            else:
                print(f"  エラー: {result['error']}")
            print()
        
        # 同時アクセステスト
        print("Testing concurrent access...")
        concurrent_result = self.test_concurrent_load('/', concurrent_users=3, requests_per_user=5)
        if concurrent_result:
            self.results.append(concurrent_result)
            print(f"  同時ユーザー数: {concurrent_result['concurrent_users']}")
            print(f"  成功率: {concurrent_result['success_rate']:.1f}%")
            print(f"  平均レスポンス時間: {concurrent_result['avg_response_time']:.2f}ms")
        print()
        
        # データベースパフォーマンステスト
        print("Testing database performance...")
        db_result = self.test_database_performance(50)
        self.results.append(db_result)
        print(f"  平均クエリ時間: {db_result['avg_response_time']:.2f}ms")
        print(f"  最大クエリ時間: {db_result['max_response_time']:.2f}ms")
        print()
        
        print("=== パフォーマンステスト完了 ===")
        
        # 結果をファイルに保存
        with open('performance_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        return self.results

def run_performance_tests():
    """パフォーマンステストを実行"""
    tester = PerformanceTester()
    return tester.run_full_performance_test()

if __name__ == "__main__":
    # アプリが起動していることを確認してからテスト実行
    print("📊 パフォーマンステストを開始します...")
    print("⚠️  アプリが http://127.0.0.1:5000 で起動していることを確認してください")
    input("準備ができたらEnterキーを押してください...")
    
    results = run_performance_tests()
    print("📋 テスト結果は 'performance_test_results.json' に保存されました")