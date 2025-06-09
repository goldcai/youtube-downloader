import os
import json
import subprocess
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import time
import traceback

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://gdget.online"}})

# yt-dlp.exe 的路径
# 优先从环境变量 YT_DLP_PATH 获取，如果未设置，则默认为与 app.py 同目录下的 yt-dlp.exe
YT_DLP_PATH = os.environ.get('YT_DLP_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), "yt-dlp.exe"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse_video', methods=['POST'])
def parse_video():
    stdout_str, stderr_str = "", "" # Initialize
    try:
        data = request.get_json()
        video_url = data.get('url')

        if not video_url:
            return jsonify({"error": "未提供视频URL"}), 400

        print(f"\n开始解析视频，URL: {video_url}")

        command = [
            YT_DLP_PATH,
            '--no-warnings',
            '--dump-json',
            '--no-playlist',
            video_url
        ]
        
        print(f"执行解析命令: {' '.join(command)}")
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True, encoding='utf-8', errors='replace') # Added errors='replace'
        stdout, stderr = process.communicate()
        
        stdout_str = stdout.strip() if stdout else "[stdout was None or empty]"
        stderr_str = stderr.strip() if stderr else "[stderr was None or empty]"

        print(f"解析命令 - 返回码: {process.returncode}")
        print(f"解析命令 - 标准输出: {stdout_str}")
        print(f"解析命令 - 错误输出: {stderr_str}")

        if process.returncode != 0:
            return jsonify({"error": f"解析视频失败: {stderr_str}"}), 500

        if not stdout_str or stdout_str == "[stdout was None or empty]":
             return jsonify({"error": f"解析视频失败: 未获取到有效的JSON输出. Stderr: {stderr_str}"}), 500

        video_info = json.loads(stdout) # stdout should be a string now

        parsed_data = {
            "title": video_info.get('title', 'N/A'),
            "description": video_info.get('description', 'N/A'),
            "thumbnail_url": video_info.get('thumbnail', 'N/A'),
            "upload_date": video_info.get('upload_date', 'N/A'),
            "file_size_approx": "N/A", 
            "video_id": video_info.get('id', video_url)
        }
        
        if parsed_data["upload_date"] != 'N/A' and len(parsed_data["upload_date"]) == 8:
            raw_date = parsed_data["upload_date"]
            parsed_data["upload_date"] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
            
        print(f"\n解析成功: {json.dumps(parsed_data, ensure_ascii=False, indent=2)}")
        return jsonify(parsed_data)

    except json.JSONDecodeError:
        print(f"JSON解析失败. stdout: {stdout_str}")
        return jsonify({"error": f"JSON解析失败. Stderr: {stderr_str}"}), 500
    except Exception as e:
        error_msg = f"解析视频时发生错误: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({"error": "服务器内部错误，请查看日志。"}), 500

@app.route('/api/download_video')
def download_video():
    temp_file_path_holder = [None]

    @after_this_request
    def cleanup_temporary_file(response):
        temp_file_to_delete = temp_file_path_holder[0]
        if temp_file_to_delete and os.path.exists(temp_file_to_delete):
            time.sleep(0.5) 
            try:
                os.remove(temp_file_to_delete)
                app.logger.info(f"成功通过 after_this_request 清理临时文件: {temp_file_to_delete}")
            except Exception as e_remove:
                app.logger.error(f"通过 after_this_request 清理临时文件 {temp_file_to_delete} 失败: {e_remove}")
        return response

    try:
        video_url = request.args.get('url')
        if not video_url:
            return jsonify({"error": "未提供视频URL"}), 400

        app.logger.info(f"开始下载视频，URL: {video_url}")
        
        title_command = [
            YT_DLP_PATH,
            '--no-warnings',
            '--get-title',
            '--no-playlist',
            '--quiet',
            video_url
        ]
        
        app.logger.info(f"获取标题命令: {' '.join(title_command)}")
        title_process = subprocess.run(title_command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        title_stdout_str = title_process.stdout.strip() if title_process.stdout else ""
        title_stderr_str = title_process.stderr.strip() if title_process.stderr else ""

        app.logger.info(f"获取标题 - 返回码: {title_process.returncode}, stdout: {title_stdout_str}, stderr: {title_stderr_str}")

        if title_process.returncode != 0 or not title_stdout_str:
            video_title = "downloaded_video" 
            app.logger.warning(f"获取标题失败或标题为空, 使用默认标题: {video_title}. Error: {title_stderr_str}")
        else:
            video_title = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title_stdout_str)

        app.logger.info(f"处理后视频标题 (用于文件名): {video_title}")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file_obj:
            temp_file_path_holder[0] = tmp_file_obj.name
        
        current_temp_file = temp_file_path_holder[0]
        app.logger.info(f"创建临时文件: {current_temp_file}")

        download_command = [
            YT_DLP_PATH,
            '--no-warnings',
            '--format', 'mp4', 
            '--no-playlist',
            '--force-overwrites', 
            '--output', current_temp_file, 
            video_url
        ]
        
        app.logger.info(f"执行下载命令: {' '.join(download_command)}")
        
        download_process = subprocess.run(download_command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        dl_stdout_str = download_process.stdout.strip() if download_process.stdout else ""
        dl_stderr_str = download_process.stderr.strip() if download_process.stderr else ""

        app.logger.info(f"下载命令 - 返回码: {download_process.returncode}")
        if dl_stdout_str: app.logger.info(f"下载命令 - stdout: {dl_stdout_str}")
        if dl_stderr_str: app.logger.warning(f"下载命令 - stderr: {dl_stderr_str}")
        
        if download_process.returncode != 0:
            return jsonify({"error": f"下载失败 (yt-dlp error): {dl_stderr_str or dl_stdout_str}"}), 500
        
        time.sleep(0.5) 

        if not os.path.exists(current_temp_file) or os.path.getsize(current_temp_file) == 0:
            error_detail = f"文件路径: {current_temp_file}, 是否存在: {os.path.exists(current_temp_file)}"
            if os.path.exists(current_temp_file):
                error_detail += f", 文件大小: {os.path.getsize(current_temp_file)}"
            app.logger.error(f"下载失败：文件未生成或为空. {error_detail}")
            return jsonify({"error": "下载失败：文件未生成或为空"}), 500
        
        file_size = os.path.getsize(current_temp_file)
        app.logger.info(f"文件下载成功. 大小: {file_size} 字节. 路径: {current_temp_file}")
        
        safe_download_name = f"{secure_filename(video_title)}.mp4"
        
        return send_file(
            current_temp_file,
            as_attachment=True,
            download_name=safe_download_name, 
            mimetype='video/mp4'
        )

    except Exception as e:
        error_msg = f"下载接口内部错误: {str(e)}\n{traceback.format_exc()}"
        app.logger.error(error_msg)
        return jsonify({"error": "服务器内部错误，请查看日志。"}), 500

if __name__ == '__main__':
    print("\n启动服务器...")
    print(f"yt-dlp.exe 路径: {YT_DLP_PATH}")
    
    try:
        print("检查 yt-dlp.exe...")
        process = subprocess.Popen([YT_DLP_PATH, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True, encoding='utf-8', errors='replace') # Added errors='replace'
        stdout, stderr = process.communicate(timeout=10) 
        
        stdout_str = stdout.strip() if stdout else ""

        if process.returncode == 0:
            print(f"yt-dlp 版本: {stdout_str}")
        else:
            stderr_str = stderr.strip() if stderr else ""
            print(f"警告: yt-dlp.exe --version 执行失败. 返回码: {process.returncode}, 错误: {stderr_str}")
            print("请确保 yt-dlp.exe 在指定路径且可执行。程序将继续尝试运行。")
    except FileNotFoundError:
        print(f"错误: yt-dlp.exe 未在 {YT_DLP_PATH} 找到！程序可能无法正常工作。")
    except subprocess.TimeoutExpired:
        print(f"警告: yt-dlp.exe --version 命令执行超时。程序将继续尝试运行。")
    except Exception as e:
        print(f"启动时检查 yt-dlp.exe 出错: {e}。程序将继续尝试运行。")
        
    app.run(debug=True, host='0.0.0.0', port=5000)