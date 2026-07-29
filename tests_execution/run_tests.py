import subprocess
import re
import os
from datetime import datetime

# ============= CONFIGS =============
BASE_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.join(BASE_REPO, "PR_Classifications/Projects/fetch/fetch")
LOG_DIRECTORY = os.path.join(BASE_REPO, "PR_Classifications")
TOTAL_RUNS = 1000
LOG_INTERVAL = 20

COMMAND = [
    'npx', 'mocha', 
    'test/core/index.test.js',
]
# ===================================

class TestLogger:
    def __init__(self, log_dir):
        self.log_buffer = []
        self.log_dir = log_dir
    
    def add_test_result(self, run_number, test_result):
        self.log_buffer.append({
            'run_number': run_number,
            'output': test_result['output'],
            'error': test_result['error'],
            'timestamp': test_result['timestamp'],
            'failed': test_result['failed'],
            'returncode': test_result['returncode']
        })
    
    def write_log_file(self, start_run, end_run):
        log_filename = os.path.join(
            self.log_dir, 
            f'test_log_{start_run}_to_{end_run}.txt'
        )
        
        os.makedirs(self.log_dir, exist_ok=True)
        
        with open(log_filename, 'w') as log_file:
            log_file.write(f'=== Test Log {start_run} to {end_run} ===\n\n')
            
            for test in self.log_buffer:
                status = "FAILED" if test['failed'] else "PASSED"
                log_file.write(f"\n=== Test #{test['run_number']} - {test['timestamp']} - {status} ===\n")
                log_file.write(test['output'])
                
                if test['failed'] or ("error" in test['error'].lower() and "PASS" not in test['error']):
                    log_file.write('\n=== ERRORS ===\n')

                log_file.write(test['error'])
                
                log_file.write(f"\nReturn code: {test['returncode']}\n")
                log_file.write('\n' + '='*80 + '\n')
            
            log_file.write('\n=== End of Log ===\n')
        
        print(f'  Logs saved to {os.path.abspath(log_filename)}')
        self.log_buffer = []

def change_to_project_root(original_dir):
    try:
        os.chdir(PROJECT_ROOT)
        print(f"Changed to project directory: {os.getcwd()}")
        return True
    except FileNotFoundError:
        print(f"Error: Project directory not found: {PROJECT_ROOT}")
        os.chdir(original_dir)
        return False

def create_log_directory():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, LOG_DIRECTORY)
    
    os.makedirs(log_dir, exist_ok=True)
    print(f"Log directory: {log_dir}")
    
    return log_dir

def run_test():
    result = subprocess.run(COMMAND, capture_output=True, text=True)
    combined_output = result.stdout + "\n" + result.stderr
    
    tests_failed = (
        result.returncode != 0 or  
        "Tests:      1 failed" in combined_output or
        "Test Suites: 1 failed" in combined_output or
        "FAIL" in combined_output
    )
    
    return {
        'output': result.stdout,
        'error': result.stderr,
        'returncode': result.returncode,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'failed': tests_failed,
        'combined_output': combined_output
    }

def extract_failed_test_info(test_result):
    output = test_result['combined_output']
    
    fail_section = re.search(
        r'(FAIL.*?Test Suites:.*?\n(.*?)\n\nTest Suites:)', 
        output, 
        re.DOTALL
    )
    
    if fail_section:
        return fail_section.group(1).strip()
    
    specific_error = re.search(
        r'(● renders category tiles.*?\n.*?\n.*?\n.*?)', 
        output
    )
    
    if specific_error:
        return specific_error.group(1).strip()
    
    fail_line = re.search(r'(FAIL.*)', output)
    if fail_line:
        return fail_line.group(1).strip()
    
    return output

def main():
    original_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = create_log_directory()
    
    project_dir_success = change_to_project_root(original_dir)
    if not project_dir_success:
        return
    
    failed_tests = []
    test_logger = TestLogger(log_dir)
    
    for run in range(1, TOTAL_RUNS + 1):
        print(f'Running test {run}/{TOTAL_RUNS}...')
        test_result = run_test()
        
        test_logger.add_test_result(run, test_result)
        
        if test_result['failed']:
            failed_info = extract_failed_test_info(test_result)
            failed_tests.append({
                'run_number': run,
                'timestamp': test_result['timestamp'],
                'info': failed_info,
                'returncode': test_result['returncode']
            })
            print(f'  Test {run} FAILED! (Code: {test_result["returncode"]})')
        
        if run % LOG_INTERVAL == 0 or run == TOTAL_RUNS:
            start_run = run - LOG_INTERVAL + 1 if run % LOG_INTERVAL == 0 else (run // LOG_INTERVAL) * LOG_INTERVAL + 1
            test_logger.write_log_file(start_run, run)
    
    os.chdir(original_dir)
    
    report_filename = os.path.join(log_dir, 'failed_tests_report.txt')
    with open(report_filename, 'w') as report_file:
        report_file.write('=== FAILED TESTS REPORT ===\n\n')
        report_file.write(f'Total tests executed: {TOTAL_RUNS}\n')
        report_file.write(f'Total failures: {len(failed_tests)}\n')
        report_file.write(f'Failure rate: {len(failed_tests)/TOTAL_RUNS*100:.2f}%\n\n')
        
        for fail in failed_tests:
            report_file.write(f'Test #{fail["run_number"]} - {fail["timestamp"]} (Code: {fail["returncode"]}):\n')
            report_file.write('\n' + '='*80 + '\n\n')
        
    if failed_tests:
        print(f'\nThere were failures!! Failed tests report saved to {os.path.abspath(report_filename)}')
    else:
        print(f'\nAll tests passed. Test report saved to {os.path.abspath(report_filename)}')

if __name__ == '__main__':
    main()