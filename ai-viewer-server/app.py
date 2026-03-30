import subprocess
import tempfile
import os
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MAX_SIZE = 50 * 1024 * 1024  # 50MB


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '파일명이 없습니다'}), 400

    data = file.read()
    if len(data) > MAX_SIZE:
        return jsonify({'error': '파일이 너무 큽니다 (최대 50MB)'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, 'input.ai')
        out_path = os.path.join(tmpdir, 'output.png')

        with open(in_path, 'wb') as f:
            f.write(data)

        result = subprocess.run([
            'gs',
            '-dNOPAUSE', '-dBATCH', '-dSAFER',
            '-sDEVICE=png16m',
            '-r150',
            '-dUseCropBox',        # PDF 기반 AI: 실제 아트보드 크기 사용
            '-dEPSCrop',           # PostScript 기반 AI: 바운딩박스 크기 사용
            '-dAutoRotatePages=/None',  # 자동 회전 방지
            '-dFirstPage=1', '-dLastPage=1',
            f'-sOutputFile={out_path}',
            in_path
        ], capture_output=True, timeout=30)

        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': '변환 실패: 지원하지 않는 파일 형식입니다'}), 422

        return send_file(out_path, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
