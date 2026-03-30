import subprocess
import tempfile
import os
import re
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MAX_SIZE = 50 * 1024 * 1024  # 50MB


def get_bounding_box(data):
    """AI/EPS 파일 헤더에서 실제 아트보드 크기 읽기."""
    header = data[:8192].decode('latin-1', errors='ignore')
    # HiResBoundingBox 우선 (더 정밀)
    match = re.search(r'%%HiResBoundingBox:\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', header)
    if not match:
        match = re.search(r'%%BoundingBox:\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', header)
    if match:
        x1, y1, x2, y2 = map(float, match.groups())
        w, h = x2 - x1, y2 - y1
        if w > 0 and h > 0:
            return w, h
    return None


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

        cmd = [
            'gs',
            '-dNOPAUSE', '-dBATCH', '-dSAFER',
            '-sDEVICE=png16m',
            '-r150',
            '-dAutoRotatePages=/None',
        ]

        bbox = get_bounding_box(data)
        if bbox:
            w, h = bbox
            cmd += [
                '-dFIXEDMEDIA',
                f'-dDEVICEWIDTHPOINTS={w}',
                f'-dDEVICEHEIGHTPOINTS={h}',
            ]
        else:
            cmd += ['-dUseCropBox']

        cmd += ['-dFirstPage=1', '-dLastPage=1', f'-sOutputFile={out_path}', in_path]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': '변환 실패: 지원하지 않는 파일 형식입니다'}), 422

        return send_file(out_path, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
