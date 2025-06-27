from flask import Flask, render_template, jsonify, request
import subprocess
import threading
import time
import os
import sys
from datetime import datetime
import json

app = Flask(__name__)

# Global variables to track execution state
execution_status = {
    'is_running': False,
    'progress': 0,
    'logs': [],
    'start_time': None,
    'end_time': None,
    'error': None,
    'current_step': '',
    'total_steps': 0,
    'current_step_progress': 0
}

def run_main_execution(batch_type='invoice'):
    """Run the main execution script in a subprocess"""
    global execution_status
    
    try:
        execution_status['is_running'] = True
        execution_status['progress'] = 0
        execution_status['logs'] = []
        execution_status['start_time'] = datetime.now().isoformat()
        execution_status['error'] = None
        execution_status['current_step'] = '準備中...'
        execution_status['total_steps'] = 3 if batch_type == 'invoice' else 2
        execution_status['current_step_progress'] = 0
        
        # Add initial log
        execution_status['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': f'=== {"請求書生成" if batch_type == "invoice" else "入金マッチング"}処理 開始 ==='
        })
        
        # Debug: Log the command being executed
        cmd = [sys.executable, 'src/main_execution.py', '--mode', batch_type]
        execution_status['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': f'実行コマンド: {" ".join(cmd)}'
        })
        
        # Debug: Log current working directory
        execution_status['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': f'作業ディレクトリ: {os.getcwd()}'
        })
        
        # Run the main execution script with specified mode
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
            cwd=os.getcwd()  # Explicitly set working directory
        )
        
        # Read output in real-time
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Parse progress information from CLI output
                    if line.startswith('[1/3]') or line.startswith('[2/3]') or line.startswith('[3/3]'):
                        # Main step progress
                        step_num = int(line[1])
                        step_text = line[4:].strip()
                        execution_status['current_step'] = step_text
                        execution_status['progress'] = int((step_num - 1) * 33.33)
                        execution_status['current_step_progress'] = 0
                    elif line.startswith('[1/2]') or line.startswith('[2/2]'):
                        # Matching step progress
                        step_num = int(line[1])
                        step_text = line[4:].strip()
                        execution_status['current_step'] = step_text
                        execution_status['progress'] = int((step_num - 1) * 50)
                        execution_status['current_step_progress'] = 0
                    elif line.startswith('  - ['):
                        # Individual project progress
                        execution_status['current_step_progress'] += 1
                        # Update progress within current step
                        if batch_type == 'invoice':
                            if 'AIによる請求書ドラフト生成' in execution_status['current_step']:
                                # 10 projects, each adds ~3.33% to the 33.33% step
                                step_progress = min(33.33, execution_status['current_step_progress'] * 3.33)
                                execution_status['progress'] = 33.33 + step_progress
                    elif line.startswith('[OK] PDF generation completed'):
                        # PDF generation completed
                        execution_status['progress'] = 66.67
                        execution_status['current_step'] = 'メール送信中...'
                    elif line.startswith('[OK] Gmail API authentication successful'):
                        # Email authentication successful
                        execution_status['progress'] = 83.33
                    elif line.startswith('[OK] Invoice email sent successfully'):
                        # Email sent successfully
                        execution_status['progress'] = 90
                    elif line.startswith('📊 Email stats:'):
                        # Email stats shown
                        execution_status['progress'] = 95
                    
                    execution_status['logs'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': line
                    })
                    # Keep only last 100 log entries
                    if len(execution_status['logs']) > 100:
                        execution_status['logs'] = execution_status['logs'][-100:]
        
        # Wait for process to complete
        return_code = process.wait()
        
        # Debug: Log return code
        execution_status['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': f'プロセス終了コード: {return_code}'
        })
        
        if return_code == 0:
            execution_status['progress'] = 100
            batch_name = "請求書生成" if batch_type == 'invoice' else "入金マッチング"
            execution_status['current_step'] = '完了'
            execution_status['logs'].append({
                'timestamp': datetime.now().isoformat(),
                'message': f'=== {batch_name}処理 完了 ==='
            })
        else:
            # Get stderr output if available
            error_details = ""
            if hasattr(process, 'stderr') and process.stderr:
                try:
                    stderr_output = process.stderr.read()
                    if stderr_output and isinstance(stderr_output, bytes):
                        error_details = f"\n詳細: {stderr_output.decode('utf-8', errors='ignore')}"
                    elif stderr_output:
                        error_details = f"\n詳細: {stderr_output}"
                except Exception as e:
                    error_details = f"\nstderr読み取りエラー: {str(e)}"
            
            # Also try to get any remaining stdout
            if hasattr(process, 'stdout') and process.stdout:
                try:
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        error_details += f"\n残りの出力: {remaining_output}"
                except Exception as e:
                    error_details += f"\nstdout読み取りエラー: {str(e)}"
            
            execution_status['error'] = f'バッチ処理がエラーで終了しました (終了コード: {return_code}){error_details}'
            execution_status['logs'].append({
                'timestamp': datetime.now().isoformat(),
                'message': f'[ERROR] エラー: 終了コード {return_code}{error_details}'
            })
            
    except Exception as e:
        execution_status['error'] = str(e)
        execution_status['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': f'[ERROR] 実行エラー: {str(e)}'
        })
        # Add traceback for debugging
        import traceback
        execution_status['logs'].append({
            'timestamp': datetime.now().isoformat(),
            'message': f'[ERROR] トレースバック: {traceback.format_exc()}'
        })
    finally:
        execution_status['is_running'] = False
        execution_status['end_time'] = datetime.now().isoformat()

@app.route('/')
def index():
    """Main page with batch execution button"""
    return render_template('web_ui.html')

@app.route('/api/start-batch', methods=['POST'])
def start_batch():
    """Start the batch execution"""
    global execution_status
    
    if execution_status['is_running']:
        return jsonify({'error': 'バッチ処理は既に実行中です'}), 400
    
    # Get batch type from request
    try:
        data = request.get_json() or {}
    except:
        data = {}
    batch_type = data.get('batch_type', 'invoice')  # Default to invoice
    
    # Validate batch type
    if batch_type not in ['invoice', 'matching']:
        return jsonify({'error': '無効なバッチ種別です'}), 400
    
    # Start execution in a separate thread
    thread = threading.Thread(target=run_main_execution, args=(batch_type,))
    thread.daemon = True
    thread.start()
    
    batch_name = "請求書生成" if batch_type == 'invoice' else "入金マッチング"
    return jsonify({'message': f'{batch_name}バッチ処理を開始しました'})

@app.route('/api/status')
def get_status():
    """Get current execution status"""
    return jsonify(execution_status)

@app.route('/api/logs')
def get_logs():
    """Get execution logs"""
    return jsonify(execution_status['logs'])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 